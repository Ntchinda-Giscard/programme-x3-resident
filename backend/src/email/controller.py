from ..database.models import EmailConfig
from ..database.session import get_db
from fastapi import APIRouter, Depends
from .model import EmailSMTPReturns, EmailConfigAdd

email_router = APIRouter(
    prefix="/email",
    tags=["email"],
)


@email_router.post("/add", response_model=EmailSMTPReturns)
async def add_email(input: EmailConfigAdd, db=Depends(get_db)):
    db_email = EmailConfig(
        smtp_server=input.smtpServer,
        user_name=input.senderEmail,
        password=input.senderPassword,
        port=input.smtpPort,
        tls=input.useTLS,
        ssl=input.useSSL,
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return EmailSMTPReturns(message="Email configuration added successfully.")