from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database.session import Base



class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    




class ConfigurationsFolders(Base):
    __tablename__ = "configurations_folders"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, unique=True, index=True)
    destination = Column(String)

class DatabaseConfiguration(Base):
    __tablename__ = "database_configuration"
    id = Column(Integer, primary_key=True, index=True)
    odbc_source = Column(String, nullable=True)
    connection_type = Column(String, nullable=False)  # 'odbc' or 'sql'
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    database = Column(String, nullable=True)
    schemas = Column(String, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)

class EmailConfig(Base):
    __tablename__ = "email_configs"
    id = Column(Integer, primary_key=True, index=True)
    smtp_server = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    password = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    receiver_email = Column(String, nullable=True)
    tls = Column(Boolean, nullable=True)
    ssl = Column(Boolean, nullable=True)
    subject = Column(String, nullable=True)
    message = Column(String, nullable=True)
    


class SiteConfig(Base):
    __tablename__ = "site_configs"
    id = Column(Integer, primary_key=True, index=True)
    site_url = Column(String, nullable=True)
    email_address = Column(String, nullable=True)