from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.comparison_view import router as comparison_view_router
from app.api.health import router as health_router
from app.api.lake_phase import router as lake_phase_router
from app.api.lakehouse_phase import router as lakehouse_phase_router
from app.api.nosql_phase import router as nosql_phase_router
from app.api.postgres_phase import router as postgres_phase_router
from app.api.warehouse_phase import router as warehouse_phase_router
from app.core.config import get_settings

app = FastAPI(title="data-infra-learn")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(postgres_phase_router)
app.include_router(nosql_phase_router)
app.include_router(warehouse_phase_router)
app.include_router(lake_phase_router)
app.include_router(lakehouse_phase_router)
app.include_router(comparison_view_router)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
