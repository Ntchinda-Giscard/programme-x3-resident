from typing import List

from fastapi import Depends
from .model import FolderSettings, SiteConfigModel
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import ConfigurationsFolders, SiteConfig


def save_folder_settings_service(folder_settings: FolderSettings, db: Session = get_db()) -> FolderSettings: # type: ignore
    db.query(ConfigurationsFolders).delete()
    db.commit()

    new_config = ConfigurationsFolders(
        source=folder_settings.source,
        destination=folder_settings.destination
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    db.close()

    return FolderSettings(source=new_config.source, destination=new_config.destination) # type: ignore


def save_site_setting( configs: List[SiteConfigModel], db: Session = get_db()) -> List[SiteConfigModel]: # type: ignore
    results = []
    for config in configs:
        new_configs = SiteConfig(
            site=config.site,
            email_address=config.email_address
        )
        results.append(new_configs)
        db.add(new_configs)
    db.commit()
    db.close()

    return results


def get_site_settting(db: Session = Depends(get_db)) -> List[SiteConfigModel]:

    response = db.query(SiteConfig).all()

    return [
        SiteConfigModel(
            site=res.site,
            email_address=res.email_address
        )
        for res in response
    ]


