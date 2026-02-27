import cv2
import requests
import time

# Load Haar Cascade classifier for frontal face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize webcam
cap = cv2.VideoCapture(0)

# Debounce/cooldown mechanism
last_trigger_time = 0
COOLDOWN_SECONDS = 10

def trigger_face_verified():
    """Send POST request to server when face is detected."""
    global last_trigger_time
    current_time = time.time()
    
    # Check if cooldown has passed
    if current_time - last_trigger_time >= COOLDOWN_SECONDS:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/event",
                json={"event": "FACE_VERIFIED"}
            )
            print(f"FACE_VERIFIED event sent! Response: {response.status_code}")
            last_trigger_time = current_time
        except requests.exceptions.RequestException as e:
            print(f"Error sending event: {e}")

print("Starting webcam... Press 'q' to quit.")

while True:
    # Capture frame from webcam
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        break
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    # Draw bounding boxes around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "Face Detected", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Trigger event if face detected (with cooldown)
    if len(faces) > 0:
        trigger_face_verified()
    
    # Display cooldown status
    time_since_last = time.time() - last_trigger_time
    if last_trigger_time > 0 and time_since_last < COOLDOWN_SECONDS:
        remaining = COOLDOWN_SECONDS - time_since_last
        cv2.putText(frame, f"Cooldown: {remaining:.1f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "Ready to detect", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Show the video feed
    cv2.imshow('VIP Face Detection', frame)
    
    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
