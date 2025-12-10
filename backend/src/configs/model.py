from pydantic import BaseModel



class FolderSettings(BaseModel):
    source: str
    destination: str


class SiteConfigModel(BaseModel):
    site: str
    email_adress: str