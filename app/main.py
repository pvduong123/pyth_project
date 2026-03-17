from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.presentation.routers.api import router as api_router
from app.presentation.routers.web import router as web_router

settings = get_settings()
configure_logging()
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(web_router)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(OperationalError)
async def handle_database_unavailable(request: Request, _: OperationalError) -> JSONResponse | HTMLResponse:
    message = "Database is unavailable. Start PostgreSQL and try again."
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=503, content={"detail": message})
    return HTMLResponse(status_code=503, content=message)
