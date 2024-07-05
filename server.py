import base64
import cv2
import numpy as np
import threading
from queue import Queue  # Importing Queue from queue module
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)
connected = False

# Initialize BLIP processor and model for image captioning
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
captioning_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/classify', methods=['POST'])
def classify():
    data_url = request.json.get('frame')
    if data_url:
        # Remove header information from base64 encoded string
        image_data = data_url.split(',')[1]
        # Decode base64 image
        img_data = base64.b64decode(image_data)
        np_img = np.frombuffer(img_data, dtype=np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        # Convert OpenCV frame to PIL Image
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Prepare inputs for the BLIP model
        inputs = processor(images=pil_image, return_tensors="pt")
        out = captioning_model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)

        return jsonify({'classification': caption})
    else:
        return jsonify({'classification': 'No frame received'})

@socketio.on('connect')
def handle_connect():
    global connected
    connected = True
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    global connected
    connected = False
    cv2.destroyAllWindows()
    print("Client disconnected")

@socketio.on('video_frame')
def handle_video_frame(data):
    # This function remains to put frames in the queue if needed for other purposes
    global frame_queue
    frame_queue.put(data)

def display_frames():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            # Process frame here if needed
            cv2.imshow('Camera Feed', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()

if __name__ == '__main__':
    frame_queue = Queue()  # Initialize Queue correctly
    display_thread = threading.Thread(target=display_frames)
    display_thread.start()

    socketio.run(app, host='0.0.0.0', port=5000)
