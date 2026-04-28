import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_backend_settings
from .pipeline.router import router as pipeline_router
from .tax_extractor.router import router as extractor_router
from .rule_retriever.router import router as retriever_router
from .tax_interpreter.router import router as interpreter_router
from .tax_calculator.router import router as calculator_router
from .auth.router import router as auth_router
from .profile.router import router as profile_router
from .sessions.router import router as sessions_router


def create_app() -> FastAPI:
    settings = get_backend_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # CORS — allow Vite dev server (5173) and common local ports
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth / profile / sessions
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(sessions_router)

    # Pipeline (primary chat endpoint)
    app.include_router(pipeline_router)

    # Individual module routers for direct access / debugging
    app.include_router(extractor_router)
    app.include_router(retriever_router)
    app.include_router(interpreter_router)
    app.include_router(calculator_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
