from pydantic import BaseModel



class FolderSettings(BaseModel):
    source: str
    destination: str


class SiteConfigModel(BaseModel):
    site_url: str
    email_address: str