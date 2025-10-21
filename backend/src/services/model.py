from typing import Optional
from pydantic import BaseModel


# --- Response Models (Optional) ---
class ServiceResponse(BaseModel):
    success: bool
    message:  Optional[str] = None
    error: Optional[str] = None
    status: Optional[bool] = None