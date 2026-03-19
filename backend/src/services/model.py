from typing import Optional
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: Optional[bool] = None
    installed: Optional[str] = None
    running: Optional[bool] = None

# --- Response Models (Optional) ---
class ServiceResponse(BaseModel):
    success: Optional[bool] = None
    message:  Optional[str] = None
    error: Optional[str] = None
    status: Optional[ServiceStatus] = None