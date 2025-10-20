from pydantic import BaseModel


# --- Response Models (Optional) ---
class ServiceResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None
    status: str | None = None