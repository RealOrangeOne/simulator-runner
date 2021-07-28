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

BASE_DIR = Path.cwd()
SIMULATION_LOCK = asyncio.Lock()

templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def homepage(request):
    return templates.TemplateResponse("index.html", {'request': request, "simulation_running": SIMULATION_LOCK.locked()})


async def run_simulation():
    async with SIMULATION_LOCK:
        now = datetime.datetime.now()
        command = shlex.split(os.environ["COMMAND"])
        print("Running simulation")
        process = await asyncio.create_subprocess_exec(*command, env={
            "OUTPUT_DIR": str(BASE_DIR / "output")
        })

        stdout, stderr = await process.communicate()
        print("Running exited with code", process.returncode)


async def submit(request):
    task = BackgroundTask(run_simulation)
    return RedirectResponse(request.url_for("homepage"), background=task)


app = Starlette(routes=[
    Route('/', homepage, name="homepage"),
    Route('/submit', submit),
    Mount('/output', app=StaticFiles(directory=BASE_DIR / "output", check_dir=False), name="static")
])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=os.environ.get("PORT", 5000),
        workers=1,
    )
