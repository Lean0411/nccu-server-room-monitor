import os, smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO  = os.getenv("ALERT_TO")

msg = MIMEText("📢 This is a test email from Raspberry Pi fire/smoke alert system.")
msg["Subject"] = "✅ TEST: Email system working"
msg["From"] = SMTP_USER
msg["To"] = ALERT_TO

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
        print("✅ 測試郵件已寄出")
except Exception as e:
    print("❌ 郵件寄送失敗:", e)
