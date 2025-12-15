import smtplib

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL = "ntchinda1998@gmail.com"      # same Gmail that created app password
APP_PASSWORD = "oclo hhnt rtbc ekkc"  # app password, NO SPACES

try:
    print("Connecting to Gmail SMTP...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)

    server.ehlo()
    server.starttls()
    server.ehlo()

    print("Logging in...")
    server.login(EMAIL, APP_PASSWORD)

    print("✅ SMTP login successful")
    server.quit()

except Exception as e:
    print("❌ SMTP test failed:")
    print(e)
