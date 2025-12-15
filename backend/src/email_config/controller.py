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
    db.query(EmailConfig).delete()
    db.commit()
    db_email = EmailConfig(
        smtp_server=input.smtpServer,
        user_name=input.senderEmail,
        receiver_email=input.receiverEmail,
        password=input.senderPassword,
        port=input.smtpPort,
        tls=input.useTLS,
        ssl=input.useSSL,
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return EmailSMTPReturns(message="Email configuration added successfully.", smtpServer = input.smtpServer,
     smtpPort = input.smtpPort,
     senderEmail = input.senderEmail,
     senderPassword = input.senderPassword,
     receiverEmail = input.receiverEmail,
     useSSL = input.useSSL,
     useTLS = input.useTLS
     )
@email_router.get("/get", response_model=EmailSMTPReturns)
async def get_email_config(db=Depends(get_db)):
    result = db.query(EmailConfig).first()
    if result is None:
        return EmailSMTPReturns(
            message="No email configuration found.",
            smtpServer="",
            smtpPort=0,
            senderEmail="",
            senderPassword="",
            receiverEmail="",
            useSSL=False,
            useTLS=False
        )
    return EmailSMTPReturns(
        message="Email configuration retrieved successfully.",
        smtpServer=result.smtp_server,
        smtpPort=result.port,
        senderEmail=result.user_name,
        receiverEmail=result.receiver_email,
        senderPassword=result.password,
        useSSL=result.ssl,
        useTLS=result.tls
    )
