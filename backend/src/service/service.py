from .model import FolderSettings
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..database.models import ConfigurationsFolders


def save_folder_settings(folder_settings: FolderSettings, db: Session = get_db()) -> FolderSettings:
    db.query(ConfigurationsFolders).delete()
    db.commit()

    new_config = ConfigurationsFolders(
        source=folder_settings.source,
        destination=folder_settings.destination
    )

    db.add(new_config)
    db.commit()
    db.refresh()
    db.close()

    return folder_settings