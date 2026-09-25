from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.postgres_phase import router as postgres_phase_router
from app.core.config import get_settings

app = FastAPI(title="data-infra-learn")

app.include_router(health_router)
app.include_router(postgres_phase_router)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
