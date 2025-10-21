from .model import FolderSettings
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import ConfigurationsFolders


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