import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import asyncio
from urllib.parse import unquote
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.core.session_store import session_store
from app.routes.health import router as health_router
from app.routes.datasets import router as datasets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start periodic session cleanup task
    cleanup_task = asyncio.create_task(session_store.start_periodic_cleanup(interval_seconds=3600))
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="CleanIQ API",
    description="Backend API for CleanIQ - Intelligent & Controlled Data Cleaning",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
ALLOWED_ORIGINS = [
    "https://cleaniq-a1f4f.web.app",
    "https://cleaniq-a1f4f.firebaseapp.com",
    "https://cleaniqqq.netlify.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Allow additional comma-separated origins via environment variable
extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
if extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared error shape exception handlers: { "error": { "code": str, "message": str } }
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Routers
app.include_router(health_router)
app.include_router(datasets_router)

# Mount Static Files & SPA Fallback Route
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_file = os.path.join(FRONTEND_DIST, "index.html")

        if full_path:
            # Check for null bytes
            if "\x00" in full_path:
                raise StarletteHTTPException(status_code=400, detail="Invalid path")

            # Decode potential multi-encoded traversal sequences
            decoded = unquote(unquote(full_path))
            if "\x00" in decoded:
                raise StarletteHTTPException(status_code=400, detail="Invalid path")

            # Block path segments attempting dot-dot relative traversal
            segments = [s.strip() for s in decoded.replace("\\", "/").split("/") if s.strip()]
            if any(s == ".." or s.startswith("..") for s in segments):
                raise StarletteHTTPException(status_code=404, detail="File not found")

            # Strip drive letters (e.g. C:) and leading slashes to prevent absolute breakout
            clean_rel = os.path.splitdrive(decoded)[1].lstrip("/\\")
            target_file = os.path.abspath(os.path.join(FRONTEND_DIST, clean_rel))

            # Strict path containment verification: target must reside within FRONTEND_DIST
            try:
                is_contained = os.path.commonpath([FRONTEND_DIST, target_file]) == FRONTEND_DIST
            except (ValueError, TypeError):
                is_contained = False

            if not is_contained:
                # Block traversal attempt outside the frontend distribution directory
                raise StarletteHTTPException(status_code=404, detail="File not found")

            # If target exists and is a regular file within FRONTEND_DIST, serve it
            if os.path.exists(target_file) and os.path.isfile(target_file):
                return FileResponse(target_file)

        # SPA fallback: client-side routes (e.g. /dashboard, /upload) serve index.html
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend build file index.html not found."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)


