import asyncio
import os
import shlex
from datetime import datetime
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple

import uvicorn
from dateutil.parser import parse as date_parse
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "output"
SIMULATION_LOCK = asyncio.Lock()

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class Output(NamedTuple):
    directory: Path

    @property
    def html_name(self) -> str:
        return next(self.directory.glob("*.html")).name

    @property
    def html_path(self) -> str:
        return f"{self.path}/{self.html_name}"

    @property
    def log_path(self) -> str:
        return f"{self.path}/logs.txt"

    @property
    def path(self) -> str:
        return self.directory.name

    @property
    def date(self) -> datetime:
        return date_parse(self.path.replace("_", ":"))

    @property
    def date_display(self) -> str:
        return self.date.strftime("%c")


def get_outputs() -> list[Output]:
    """
    Different recordings are based on their result slug
    """
    return sorted(
        [Output(d) for d in OUTPUT_DIR.iterdir() if d.is_dir()], key=attrgetter("date")
    )


async def homepage(request: Request) -> Response:
    outputs = await asyncio.to_thread(get_outputs)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "simulation_running": SIMULATION_LOCK.locked(),
            "outputs": outputs,
        },
    )


async def run_simulation() -> None:
    async with SIMULATION_LOCK:
        command = shlex.split(os.environ["COMMAND"])
        print("Running simulation")
        process = await asyncio.create_subprocess_exec(
            *command, env={"OUTPUT_DIR": str(OUTPUT_DIR)}
        )

        await asyncio.wait_for(process.communicate(), 150)
        print("Running exited with code", process.returncode)


async def submit(request: Request) -> RedirectResponse:
    if SIMULATION_LOCK.locked():
        return RedirectResponse(request.url_for("homepage"))
    task = BackgroundTask(run_simulation)
    return RedirectResponse(request.url_for("homepage"), background=task)


app = Starlette(
    routes=[
        Route("/", homepage, name="homepage"),
        Route("/submit", submit),
        Mount(
            "/output",
            app=StaticFiles(directory=OUTPUT_DIR, check_dir=False),
            name="output",
        ),
    ],
    middleware=[Middleware(GZipMiddleware)],
)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=os.environ.get("PORT", 5000),
        workers=1,
    )
