from pydantic import BaseModel
from typing import List, Optional

class EmailSMTPReturns(BaseModel):
    message: str



class  EmailConfigAdd(BaseModel):
  smtpServer: str
  smtpPort: int
  senderEmail: str
  senderPassword: str
  useSSL: bool
  useTLS: bool
  