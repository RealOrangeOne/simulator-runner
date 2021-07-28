from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
import uvicorn
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

BASE_DIR = Path.cwd()

templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def homepage(request):
    return templates.TemplateResponse("index.html", {'request': request})


async def submit(request):
    return RedirectResponse(request.url_for("homepage"))


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
