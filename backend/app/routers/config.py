"""GET /api/config — owner name for the UI. No DB hit; doubles as the health check."""

from fastapi import APIRouter

from .. import config
from ..models import ConfigResponse

router = APIRouter()


@router.get("/api/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(owner_name=config.OWNER_NAME)
