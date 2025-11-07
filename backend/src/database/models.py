from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database.session import Base

class ConfigurationsFolders(Base):
    __tablename__ = "configurations_folders"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, unique=True, index=True)
    destination = Column(String)

class DatabaseConfiguration(Base):
    __tablename__ = "database_configuration"
    id = Column(Integer, primary_key=True, index=True)
    odbc_source = Column(String, unique=True, nullable=False)
    connection_type = Column(String, nullable=False)
    host = Column(String, unique=True, index=True)
    port = Column(Integer)
    name = Column(String)
    user = Column(String)
    password = Column(String)
    