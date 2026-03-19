from typing import List
from fastapi import APIRouter, Depends
from .model import FolderSettings, SiteConfigModel
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import ConfigurationsFolders
from .service import delete_site_setting, get_site_settting, save_folder_settings_service, save_site_setting

folder_router = APIRouter(
    prefix="/config",
    tags=["folder configurations"]
)


@folder_router.post("/add", response_model=FolderSettings)
def save_folder_settings(folder_settings: FolderSettings, db: Session = Depends(get_db)):
    return save_folder_settings_service(folder_settings, db)


@folder_router.get("/get", response_model=FolderSettings)
def get_folder_settings(db: Session = Depends(get_db)):
    response = db.query(ConfigurationsFolders).first()
    return FolderSettings(
        source=response.source, # type: ignore
        destination=response.destination # type: ignore
    )

@folder_router.post("/add/address", response_model=List[SiteConfigModel])
def insert_config(configs: List[SiteConfigModel], db: Session = Depends(get_db)):
    return save_site_setting(configs, db)

@folder_router.get("/get/address", response_model=List[SiteConfigModel])
def get_config(db: Session = Depends(get_db)):
    return get_site_settting(db)

@folder_router.delete("/delete/address/{site}")
def delete_config(site: str, db: Session = Depends(get_db)):
    return delete_site_setting(site, db)