#!/usr/bin/env python3
import os, time, io, zipfile, smtplib, subprocess
from collections import deque
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv
from PIL import Image
import board, digitalio

# 讀取 SMTP 設定
load_dotenv()
HOST, PORT = os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))
USER, PASS = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")
ALERT_TO   = os.getenv("ALERT_TO")

# 參數
BUFFER_SIZE  = 20            # 保留最近 20 張
CAP_INTERVAL = 5             # 每 5 秒拍一次
ROI = (100, 80, 200, 150)    # (x,y,w,h)
OUT_DIR = "captures"
TMP_JPG = "/tmp/cam_tmp.jpg"
os.makedirs(OUT_DIR, exist_ok=True)

# 感測器
mq2   = digitalio.DigitalInOut(board.D17); mq2.direction  = digitalio.Direction.INPUT
flame = digitalio.DigitalInOut(board.D27); flame.direction= digitalio.Direction.INPUT

buffer = deque(maxlen=BUFFER_SIZE)

def take_photo():
    """用 raspistill 拍照到 /tmp/cam_tmp.jpg，回傳 PIL.Image"""
    subprocess.run(["raspistill","-n","-w","640","-h","480","-o",TMP_JPG], check=True)
    return Image.open(TMP_JPG)

def send_zip(event_type, zip_bytes):
    msg = MIMEMultipart()
    msg["Subject"] = f"[Alert] {event_type} detected {datetime.now().isoformat(sep=' ', timespec='seconds')}"
    msg["From"], msg["To"] = USER, ALERT_TO
    msg.attach(MIMEText(f"{event_type} 觸發。附件為最近 {len(buffer)} 張 ROI。", "plain"))
    part = MIMEBase("application","zip")
    part.set_payload(zip_bytes.getvalue())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{event_type}.zip"')
    msg.attach(part)
    with smtplib.SMTP(HOST,PORT) as s:
        s.starttls(); s.login(USER,PASS); s.send_message(msg)
    print("📧 Mail sent.")

def save_and_mail(event_type, entries):
    """把 entries 打包成 zip（磁碟+Email）"""
    ts_tag = entries[-1]['ts'].replace(' ','T')
    zip_path = os.path.join(OUT_DIR, f"{event_type}_{ts_tag}.zip")
    with zipfile.ZipFile(zip_path,"w") as zf:
        for i,e in enumerate(entries):
            fn = f"{event_type}_{i+1}_{e['ts'].replace(' ','T')}.jpg"
            zf.writestr(fn, e['img_bytes'])
    # 同時用 BytesIO 再寄出
    buf = io.BytesIO(open(zip_path,'rb').read())
    send_zip(event_type, buf)

print("★ Monitor started (raspistill version)…")

try:
    while True:
        ts = datetime.now().isoformat(sep=' ', timespec='seconds')
        img_full = take_photo()
        x,y,w,h = ROI
        roi = img_full.crop((x,y,x+w,y+h))
        img_buf = io.BytesIO(); roi.save(img_buf, format="JPEG"); img_bytes = img_buf.getvalue()

        smoke = not mq2.value    # LOW→True
        fire  = not flame.value  # LOW→True
        buffer.append({"ts":ts, "img_bytes":img_bytes})

        print(f"[{ts}] smoke={smoke} fire={fire}")
        if smoke or fire:
            etype = "SMOKE" if smoke else "FIRE"
            print(f">>> {etype} detected!  Saving + mailing buffer…")
            save_and_mail(etype, list(buffer))
        time.sleep(CAP_INTERVAL)
except KeyboardInterrupt:
    print("Exit.")
