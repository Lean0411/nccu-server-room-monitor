import os, smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO  = os.getenv("ALERT_TO")

# 測試郵件內容
test_message = """NCCU 政治大學機房監控系統 - 郵件功能測試

測試時間：{test_time}
測試位置：NCCU 大仁樓 1F（樓梯旁）機房

系統狀態：
- 監控系統正常運行
- 感測器連線正常
- 郵件發送功能正常
- 網路連線穩定

系統管理員：
李恩甫同學
電話：0958-242-580

此為系統功能測試郵件，如收到此郵件表示警報通知系統運作正常。

NCCU 機房監控系統
政治大學資訊處""".format(test_time=__import__('datetime').datetime.now().strftime('%Y年%m月%d日 %H時%M分%S秒'))

msg = MIMEText(test_message)
msg["Subject"] = "[測試郵件] NCCU 機房監控系統功能測試"
msg["From"] = SMTP_USER
msg["To"] = ALERT_TO

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
        print("測試郵件已成功寄出")
except Exception as e:
    print("郵件寄送失敗:", e)
