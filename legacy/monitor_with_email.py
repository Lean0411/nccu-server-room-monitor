#!/usr/bin/env python3
import os, time, io, zipfile, smtplib
from collections import deque
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from picamera import PiCamera
from PIL import Image
import board, digitalio
from dotenv import load_dotenv
import numpy as np

# load SMTP settings from .env
load_dotenv()
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO   = os.getenv("ALERT_TO")

# config
BUFFER_SIZE  = 20
CAP_INTERVAL = 5
ROI = (100, 80, 200, 150)
OUT_DIR = "captures"
os.makedirs(OUT_DIR, exist_ok=True)

# setup sensors and camera
mq2 = digitalio.DigitalInOut(board.D17); mq2.direction = digitalio.Direction.INPUT
flame = digitalio.DigitalInOut(board.D27); flame.direction = digitalio.Direction.INPUT
camera = PiCamera()
camera.resolution = (640, 480)
camera.start_preview()
time.sleep(2)

buffer = deque(maxlen=BUFFER_SIZE)

def capture_roi():
    stream = io.BytesIO()
    camera.capture(stream, format='jpeg')
    stream.seek(0)
    img = Image.open(stream).convert("RGB")
    np_img = np.array(img)
    x, y, w, h = ROI
    roi = np_img[y:y+h, x:x+w].copy()
    return roi

def send_event_email(event_type, zip_bytes):
    msg = MIMEMultipart()
    msg["Subject"] = f"[Alert] {event_type} detected at {datetime.now().isoformat()}"
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_TO
    msg.attach(MIMEText(f"{event_type} detected. Attached is last {len(buffer)} frames.", "plain"))
    part = MIMEBase("application", "zip")
    part.set_payload(zip_bytes.getvalue())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{event_type}.zip"')
    msg.attach(part)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def save_event(event_type, entries):
    zip_path = os.path.join(OUT_DIR, f"{event_type}_{entries[-1]['ts'].replace(' ', 'T')}.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i, e in enumerate(entries):
            fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
            img_path = os.path.join(OUT_DIR, fn)
            Image.fromarray(e["img"]).save(img_path)
            zf.write(img_path, arcname=fn)
    with io.BytesIO() as buf:
        with zipfile.ZipFile(buf, "w") as zf:
            for i, e in enumerate(entries):
                fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
                im = Image.fromarray(e["img"])
                with io.BytesIO() as img_buf:
                    im.save(img_buf, format="JPEG")
                    zf.writestr(fn, img_buf.getvalue())
        buf.seek(0)
        send_event_email(event_type, buf)

print(f"Monitoring... buffer size={BUFFER_SIZE}, interval={CAP_INTERVAL}s")
try:
    while True:
        ts = datetime.now().isoformat(sep=" ", timespec="seconds")
        roi = capture_roi()
        smoke = not mq2.value
        fire  = not flame.value
        entry = {"ts": ts, "img": roi, "smoke": smoke, "fire": fire}
        buffer.append(entry)
        print(f"[{ts}] smoke={smoke} fire={fire}")
        if smoke or fire:
            ev = "SMOKE" if smoke else "FIRE"
            print(f">>> {ev} event! saving and emailing buffer...")
            save_event(ev, list(buffer))
        time.sleep(CAP_INTERVAL)
except KeyboardInterrupt:
    print("Stopped.")
finally:
    camera.close()
