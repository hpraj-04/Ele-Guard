from flask import Flask, jsonify
import cv2
from ultralytics import YOLO
import threading
import sqlite3
from datetime import datetime
import time
import os
import pygame
from twilio.rest import Client

app = Flask(__name__)

# ---------------- YOLO MODEL ----------------
model = YOLO("yolov8m.pt")   # stronger model

# ---------------- SYSTEM VARIABLES ----------------
elephant_present = False
last_detection_time = 0
cooldown_seconds = 5
current_mood = "Calm"

# ---------------- LOCATION ----------------
# ---------------- LOCATION ----------------
latitude = YOUR_LATITUDE
longitude = YOUR_LONGITUDE
location_link = f"https://maps.google.com/?q={latitude},{longitude}"

# ---------------- TWILIO CONFIG (UNCHANGED) ----------------
# Twilio Configuration
account_sid = "YOUR_TWILIO_ACCOUNT_SID"
auth_token = "YOUR_TWILIO_AUTH_TOKEN"

twilio_phone = "YOUR_TWILIO_PHONE_NUMBER"

villager_phone = "VILLAGER_PHONE_NUMBER"
forest_officer_phone = "FOREST_OFFICER_PHONE_NUMBER"

client = Client(account_sid, auth_token)

# ---------------- SOUND SETUP ----------------
pygame.mixer.init()

def play_alarm():
    try:
        pygame.mixer.music.load("alarm.mp3")
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
    except:
        print("Alarm sound file missing")

# ---------------- SNAPSHOT FOLDER ----------------
if not os.path.exists("snapshots"):
    os.makedirs("snapshots")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("elephant.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    mood TEXT,
    image_path TEXT
)
""")
conn.commit()

# ---------------- IMAGE-BASED MOOD CLASSIFICATION ----------------
prev_mood = "Calm"

def classify_mood(frame, box):

    global prev_mood

    x1, y1, x2, y2 = map(int, box.xyxy[0])

    roi = frame[y1:y2, x1:x2]

    if roi.size == 0:
        return prev_mood

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    edge_count = cv2.countNonZero(edges)

    # Shape
    h, w = gray.shape
    ratio = h / w

    # -------- RULES --------
    if edge_count > 5000 or ratio < 0.9:
        mood = "Aggressive"
    elif edge_count > 2500 or ratio < 1.2:
        mood = "Stressed"
    else:
        mood = "Calm"

    prev_mood = mood
    return mood

# ---------------- SAVE DETECTION ----------------
def log_detection(mood, frame):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"snapshots/{timestamp}.jpg"

    cv2.imwrite(filename, frame)

    cursor.execute(
        "INSERT INTO detections (timestamp, mood, image_path) VALUES (?, ?, ?)",
        (timestamp, mood, filename)
    )

    conn.commit()

# ---------------- SEND SMS (UNCHANGED) ----------------
def send_sms_alert(mood):

    message = f"""
⚠️ Elephant Alert!

Behavior: {mood}

Avoid this area.

Location:
{location_link}

Forest Officer:
+91 9876543210
"""

    try:

        client.messages.create(
            body=message,
            from_=twilio_phone,
            to=villager_phone
        )

        client.messages.create(
            body=message,
            from_=twilio_phone,
            to=forest_officer_phone
        )

        print("SMS alerts sent")

    except Exception as e:
        print("SMS failed:", e)

# ---------------- CAMERA DETECTION ----------------
def camera_detection():

    global elephant_present, last_detection_time, current_mood

    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        frame = cv2.resize(frame,(960,540))

        # Improved detection
        results = model(frame, conf=0.15, imgsz=1280)

        detected = False

        for r in results:

            for box in r.boxes:

                class_id = int(box.cls)

                if class_id == 20:   # elephant class

                    detected = True

                    mood = classify_mood(frame, box)
                    current_mood = mood

                    x1,y1,x2,y2 = map(int,box.xyxy[0])

                    color = (0,255,0)

                    if mood == "Aggressive":
                        color = (0,0,255)
                    elif mood == "Stressed":
                        color = (0,165,255)

                    cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)

                    cv2.putText(frame,mood,(x1,y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                color,
                                2)

        # If no detection
        if not detected:
            cv2.putText(frame,"No Elephant Detected",
                        (50,50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0,0,255),
                        2)

        # ALERT SYSTEM
        if detected:

            current_time = time.time()

            if current_time - last_detection_time > cooldown_seconds:

                elephant_present = True
                last_detection_time = current_time

                print("Elephant Encounter:", current_mood)

                log_detection(current_mood, frame)
                play_alarm()
                send_sms_alert(current_mood)

        else:
            elephant_present = False

        cv2.imshow("EleGuard AI Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ---------------- API ----------------
@app.route('/status')
def status():

    return jsonify({
        "elephant": elephant_present,
        "mood": current_mood
    })

# ---------------- MAIN ----------------
if __name__ == '__main__':

    threading.Thread(target=camera_detection).start()
    app.run(host='0.0.0.0', port=5000)
