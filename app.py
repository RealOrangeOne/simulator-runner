from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
import uvicorn
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.background import BackgroundTask
import asyncio
import datetime
import shlex
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware import Middleware

BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "output"
SIMULATION_LOCK = asyncio.Lock()

templates = Jinja2Templates(directory=BASE_DIR / "templates")


def get_output_slugs():
    """
    Different recordings are based on their result slug
    """
    output_slugs = []
    for html_file in OUTPUT_DIR.glob("*.html"):
        output_slugs.append(html_file.stem)
    return sorted(output_slugs)



async def homepage(request):
    output_slugs = await asyncio.to_thread(get_output_slugs)
    return templates.TemplateResponse("index.html", {'request': request, "simulation_running": SIMULATION_LOCK.locked(), "output_slugs": output_slugs})


async def run_simulation():
    async with SIMULATION_LOCK:
        now = datetime.datetime.now()
        command = shlex.split(os.environ["COMMAND"])
        print("Running simulation")
        process = await asyncio.create_subprocess_exec(*command, env={
            "OUTPUT_DIR": str(OUTPUT_DIR)
        })

        stdout, stderr = await process.communicate()
        print("Running exited with code", process.returncode)


async def submit(request):
    task = BackgroundTask(run_simulation)
    return RedirectResponse(request.url_for("homepage"), background=task)


app = Starlette(
    routes=[
        Route('/', homepage, name="homepage"),
        Route('/submit', submit),
        Mount('/output', app=StaticFiles(directory=OUTPUT_DIR, check_dir=False), name="output")
    ],
    middleware=[Middleware(GZipMiddleware)]
)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=os.environ.get("PORT", 5000),
        workers=1,
    )
