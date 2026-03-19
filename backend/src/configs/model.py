from pydantic import BaseModel



class FolderSettings(BaseModel):
    source: str
    destination: str


class SiteConfigModel(BaseModel):
    site: str
    email_address: str