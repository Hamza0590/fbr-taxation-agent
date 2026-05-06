import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_backend_settings, get_cors_settings
from .pipeline.router import router as pipeline_router
from .tax_extractor.router import router as extractor_router
from .rule_retriever.router import router as retriever_router
from .tax_interpreter.router import router as interpreter_router
from .tax_calculator.router import router as calculator_router
from .auth.router import router as auth_router
from .profile.router import router as profile_router
from .sessions.router import router as sessions_router
from .image_extractor.router import router as image_extractor_router


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

    # CORS — origins are configured via CORS_ALLOWED_ORIGINS in .env
    cors = get_cors_settings()
    origins = [o.strip() for o in cors.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
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
    app.include_router(image_extractor_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
