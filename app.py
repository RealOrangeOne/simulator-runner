import asyncio
import os
import shlex
import subprocess
from datetime import datetime
from enum import Enum
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


def safe_parse_date(data: str) -> Optional[datetime]:
    try:
        return date_parse(data.split('@')[0].replace("_", ":"))
    except ParserError:
        return None


class OutputType(Enum):
    PRACTICE = 0
    FRIENDLY = 1
    COMPETITION = 2


class Output(NamedTuple):
    directory: Path

    @property
    def html_path(self) -> Optional[str]:
        try:
            html_name = next(self.directory.glob("*.html")).name
        except StopIteration:
            return None

        return f"{self.path}/{html_name}"

    @property
    def log_path(self) -> Optional[str]:
        if not (self.directory / "logs.txt").is_file():
            return None
        return f"{self.path}/logs.txt"

    @property
    def path(self) -> str:
        return self.directory.name

    @property
    def date(self) -> Optional[datetime]:
        return safe_parse_date(self.path)

    @property
    def display(self) -> str:
        date = self.date
        if date:
            return date.strftime("%c")
        return self.path

    @property
    def output_type(self) -> OutputType:
        return parse_output_type(self.path)
    
    @property
    def zone(self) -> Optional[int]:
        return parse_zone(self.path)
    

def parse_output_type(data: str) -> OutputType:
    split_data = data.split('@')
    if len(split_data) > 1:
        if split_data[1] == "competition":
            return OutputType.COMPETITION
        elif split_data[1] == "friendly":
            return OutputType.FRIENDLY
    return OutputType.PRACTICE

def parse_zone(data:str) -> Optional[int]:
    split_data = data.split('@')
    if len(split_data) > 2:
        return int(split_data[2])
    else:
        return None

def get_outputs() -> list[Output]:
    """
    Different recordings are based on their result slug
    """
    return sorted(
        [
            Output(d)
            for d in OUTPUT_DIR.iterdir()
            if d.is_dir() and safe_parse_date(d.name)
        ],
        key=attrgetter("display"),
        reverse=True,
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
    process = subprocess.run(
        command,
        env={**os.environ, "OUTPUT_DIR": str(OUTPUT_DIR), "PYTHONHASHSEED": "0"},
        timeout=150,
    )
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
