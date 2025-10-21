from fastapi import APIRouter, Depends
from .model import FolderSettings
from sqlalchemy.orm import Session
from ..database.session import get_db
from .service import save_folder_settings_service

folder_router = APIRouter(
    prefix="/config",
    tags=["folder configurations"]
)


@folder_router.post("/add", response_model=FolderSettings)
def save_folder_settings(folder_settings: FolderSettings, db: Session = Depends(get_db)):
    return save_folder_settings_service(folder_settings, db)
