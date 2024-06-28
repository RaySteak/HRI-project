import face_recognition
import cv2
import numpy as np
import socket
import torch
from transformers import ViTFeatureExtractor, ViTForImageClassification, AutoConfig

device = 'cuda' if torch.cuda.is_available() else 'cpu'

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, SERVER_PORT))

s.sendall('f'.encode())

# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)

# Create arrays of known face encodings and their names
known_face_encodings = []

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

# Load the ViT model
MODEL_URL = 'nateraw/vit-age-classifier'
model = ViTForImageClassification.from_pretrained(MODEL_URL).to(device)
model.eval()
transforms = ViTFeatureExtractor.from_pretrained(MODEL_URL)
config = AutoConfig.from_pretrained(MODEL_URL)



while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()

    # Only process every other frame of video to save time
    if process_this_frame:
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        # rgb_small_frame = small_frame[:, :, ::-1]
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        rgb_small_frame = np.array(rgb_small_frame)
        
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        if len(face_locations) != 0:
            # Take only first face
            # TODO: maybe treat the case of multiple faces
            face_location = face_locations[0]
            face_encoding = face_encodings[0]
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            
            # Get the face from the frame and run inference
            with torch.no_grad():
                face = frame[top:bottom, left:right]
                transformed_face = transforms(face, return_tensors = 'pt').to(device)
                out = model(**transformed_face)
                age_range_id = torch.argmax(out.logits).item()

            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            
            try:
                match_key = matches.index(True)
                print(f'ID: {match_key} AGE: {config.id2label[age_range_id]}')
            except ValueError:
                print("FOUND UNKNOWN FACE, SAVING...")
                known_face_encodings.append(face_encoding)
                match_key = len(known_face_encodings) - 1
            
            # Send the match key to the server
            s.sendall(("Face %04d %02d" % (match_key, age_range_id)).encode())
        else:
            s.sendall("Face      NO".encode())

        # face_names.append(name)

    process_this_frame = not process_this_frame


    # Display the results
    for top, right, bottom, left in face_locations:
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, "person", (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
        

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()