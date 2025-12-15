import smtplib
import email.utils

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL = "yourgmail@gmail.com"          # the Gmail that created the App Password
APP_PASSWORD = "oclo hhnt rtbc ekkc"      # 16-char app password, NO SPACES

try:
    print("Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)

    server.ehlo()
    server.starttls()
    server.ehlo()

    print("Logging in...")
    server.login(EMAIL, APP_PASSWORD.replace(" ", ""))

    print("✅ SMTP login successful!")
    server.quit()

except Exception as e:
    print("❌ SMTP login failed:")
    print(e)
