from ..database.models import EmailConfig
from ..database.session import get_db
from fastapi import APIRouter, Depends
from .model import EmailSMTPReturn

email_router = APIRouter(
    prefix="/email",
    tags=["email"],
)


@email_router.post("/add", response_model=EmailSMTPReturn)
async def add_email(input: EmailConfig, db=Depends(get_db)):
    db_email = EmailConfig(
        smtp_server=input.smtp_server,
        user_name=input.user_name,
        password=input.password,
        port=input.port,
        tls=input.tls,
        ssl=input.ssl,
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return EmailSMTPReturn(message="Email configuration added successfully.")