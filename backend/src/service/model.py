from pydantic import BaseModel



class FolderSettings(BaseModel):
    source: str
    destination: str