# schemas.py
from pydantic import BaseModel
from typing import List, Optional

from sqlalchemy import Column

class DatabaseServerAdd(BaseModel):
    odbc_source: str
    connection_type: str
    db_type: Optional[str] = None
    db_server: Optional[str] = None
    db_username: Optional[str] = None
    db_password: Optional[str] = None