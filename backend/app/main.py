"""FastAPI app assembly: API routers first, then the built static frontend.

GET /       -> frontend/dist/index.html  (visitor chat)
GET /admin  -> frontend/dist/admin.html  (admin dashboard)
Everything else in frontend/dist (hashed assets, icons, avatar images) is
served by a catch-all static mount registered after the API routes.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST
from .routers import admin, chat, config as config_router

app = FastAPI(title="Avatar", docs_url=None, redoc_url=None)

app.include_router(config_router.router)
app.include_router(chat.router)
app.include_router(admin.router)


if FRONTEND_DIST.exists():

    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(FRONTEND_DIST / "admin.html")

    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
