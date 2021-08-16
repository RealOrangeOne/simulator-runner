import asyncio
import os
import shlex
import subprocess
from datetime import datetime
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple, Optional

import uvicorn
from dateutil.parser import ParserError
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
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", BASE_DIR / "output")).resolve()
SIMULATION_LOCK = asyncio.Lock()

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class Output(NamedTuple):
    directory: Path

    @property
    def html_name(self) -> Optional[str]:
        return next(self.directory.glob("*.html")).name

    @property
    def html_path(self) -> Optional[str]:
        return f"{self.path}/{self.html_name}"

    @property
    def log_path(self) -> str:
        return f"{self.path}/logs.txt"

    @property
    def path(self) -> str:
        return self.directory.name

    @property
    def date(self) -> Optional[datetime]:
        try:
            return date_parse(self.path.replace("_", ":"))
        except ParserError:
            return None

    @property
    def display(self) -> str:
        date = self.date
        if date:
            return date.strftime("%c")
        return self.path

    def is_valid(self) -> bool:
        return (
            self.html_path is not None
            and self.date is not None
            and os.path.exists(self.log_path)
        )


def get_outputs() -> list[Output]:
    """
    Different recordings are based on their result slug
    """
    return sorted(
        [Output(d) for d in OUTPUT_DIR.iterdir() if d.is_dir()],
        key=attrgetter("display"),
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


def _actually_run_simulation() -> int:
    command = shlex.split(os.environ["COMMAND"])
    process = subprocess.run(command, env={"OUTPUT_DIR": str(OUTPUT_DIR)}, timeout=150)
    return process.returncode


async def run_simulation() -> None:
    async with SIMULATION_LOCK:
        print("Running simulation")
        return_code = await asyncio.to_thread(_actually_run_simulation)
        print("Running exited with code", return_code)


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
    if not OUTPUT_DIR.exists():
        print(f"Creating output directory at {OUTPUT_DIR}")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("COMMAND"):
        print(
            "Warning: no command specified. Set the 'COMMAND' environment "
            "variable to specify how to run the simulator.",
        )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=os.environ.get("PORT", 5000),
        workers=1,
    )
