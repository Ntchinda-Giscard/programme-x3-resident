from pydantic import BaseModel
from typing import List, Optional

class EmailSMTPReturns(BaseModel):
    message: str
    smtpServer: str
    smtpPort: int
    senderEmail: str
    receiverEmail: str
    senderPassword: str
    useSSL: bool
    useTLS: bool



class  EmailConfigAdd(BaseModel):
  smtpServer: str
  smtpPort: int
  senderEmail: str
  receiverEmail: str
  senderPassword: str
  useSSL: bool
  useTLS: bool
  