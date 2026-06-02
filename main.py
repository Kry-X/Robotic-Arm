import cv2
import mediapipe as mp
import serial
import time
import math
import warnings

warnings.filterwarnings("ignore")

# ==========================
# SERIAL PORT
# ==========================
ser = serial.Serial("COM3", 115200, timeout=1)
time.sleep(2)

# ==========================
# SEND SETTINGS
# ==========================
SEND_INTERVAL = 0.1  # 10 updates/sec
last_send = 0

# ==========================
# SMOOTHING
# ==========================
SMOOTH = 0.15

# ==========================
# MEDIAPIPE HANDS
# ==========================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# ==========================
# CAMERA
# ==========================
cap = cv2.VideoCapture(0)

# ==========================
# INITIAL SERVO POSITIONS
# ==========================
base = 55
elbow = 26
wrist = 75
claw = 30


def smooth(old, new):
    return old + (new - old) * SMOOTH


while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    result = hands.process(rgb)

    if result.multi_hand_landmarks:

        hand = result.multi_hand_landmarks[0]

        mp_draw.draw_landmarks(
            frame,
            hand,
            mp_hands.HAND_CONNECTIONS
        )

        # Landmarks
        thumb_tip = hand.landmark[4]
        index_tip = hand.landmark[8]
        pinky_tip = hand.landmark[20]

        # ==================================
        # BASE SERVO (0 - 110)
        # LEFT -> RIGHT
        # ==================================
        target_base = int(index_tip.x * 110)

        # ==================================
        # ELBOW SERVO (0 - 53)
        # DOWN -> UP
        # ==================================
        target_elbow = int((1 - index_tip.y) * 53)

        # ==================================
        # WRIST SERVO (27 - 123)
        # PALM ROTATION
        # ==================================
        dx = pinky_tip.x - index_tip.x
        dy = pinky_tip.y - index_tip.y

        palm_angle = math.degrees(
            math.atan2(dy, dx)
        )

        normalized = (palm_angle + 180) / 360

        target_wrist = int(
            27 + normalized * (123 - 27)
        )

        target_wrist = max(
            27,
            min(123, target_wrist)
        )

        # ==================================
        # CLAW SERVO (5 - 59)
        # THUMB ↔ INDEX DISTANCE
        # ==================================
        distance = math.hypot(
            thumb_tip.x - index_tip.x,
            thumb_tip.y - index_tip.y
        )

        distance = max(
            0.03,
            min(0.25, distance)
        )

        target_claw = int(
            5 +
            ((distance - 0.03) / (0.25 - 0.03))
            * (59 - 5)
        )

        target_claw = max(
            5,
            min(59, target_claw)
        )

        # ==================================
        # SMOOTHING
        # ==================================
        base = smooth(base, target_base)
        elbow = smooth(elbow, target_elbow)
        wrist = smooth(wrist, target_wrist)
        claw = smooth(claw, target_claw)

        # ==================================
        # LIMITS
        # ==================================
        base = max(0, min(110, int(base)))
        elbow = max(0, min(53, int(elbow)))
        wrist = max(27, min(123, int(wrist)))
        claw = max(5, min(59, int(claw)))

        # ==================================
        # SERIAL PACKET
        # ==================================
        packet = (
            f"B{base},"
            f"E{elbow},"
            f"W{wrist},"
            f"C{claw}\n"
        )

        # ==================================
        # SEND TO ESP32
        # ==================================
        current_time = time.time()

        if current_time - last_send >= SEND_INTERVAL:

            ser.write(packet.encode())

            print("Sent:", packet.strip())

            last_send = current_time

        # ==================================
        # DISPLAY VALUES
        # ==================================
        cv2.putText(
            frame,
            f"Base : {base}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Elbow: {elbow}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Wrist: {wrist}",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Claw : {claw}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            packet.strip(),
            (10, 160),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )

    cv2.imshow(
        "Gesture Controlled Robotic Arm",
        frame
    )

    key = cv2.waitKey(1)

    if key == 27:  # ESC key
        break

cap.release()
ser.close()
cv2.destroyAllWindows()