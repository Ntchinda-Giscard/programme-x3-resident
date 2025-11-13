from pydantic import BaseModel
from typing import List, Optional

class EmailSMTPReturn(BaseModel):
    message: str



class  EmailConfig(BaseModel):
  smtpServer: str
  smtpPort: int
  senderEmail: str
  senderPassword: str
  useSSL: bool
  useTLS: bool
  