# schemas.py
from pydantic import BaseModel
from typing import List, Optional

from sqlalchemy import Column

class DatabaseServerAdd(BaseModel):
    odbc_source: Optional[str] = None
    connection_type: str  # 'odbc' or 'sql'
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None