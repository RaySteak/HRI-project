# import os, sys
# import time

# sys.path.append(os.getenv('PEPPER_TOOLS_HOME')+'/cmd_server')

# import pepper_cmd
# from pepper_cmd import *

# begin()

# pepper_cmd.robot.say('Hello')
# pepper_cmd.robot.forward(5)
# pepper_cmd.robot.turn(90)

# end()

import os, qi
import time
import math
from PIL import Image
import numpy as np
import socket
from threading import Thread

pip = os.getenv('PEPPER_IP')
pport = 44293
url = "tcp://" + pip + ":" + str(pport)

host = ''
port = 12345
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))
s.listen(2)

def set_conn(conn, conn_type):
    global conn_face
    global conn_frontend
    
    if conn_type == 'f': # face recognition
        conn_face = conn
        print("Face recognition connected")
    elif conn_type == 'i': # interface (frontend)
        print("Frontend connected")
        conn_frontend = conn
        

conn, addr = s.accept()
conn_type = conn.recv(1).decode('utf-8')
set_conn(conn, conn_type)

conn, addr = s.accept()
conn_type = conn.recv(1).decode('utf-8')
set_conn(conn, conn_type)

face_to_delete = None
def frontend_recv_task():
    global face_to_delete
    
    while True:
        r = conn_frontend.recv(5)
        print(r)
        if r.startswith('D'):
            face_to_delete = int(r[1:])
t = Thread(target = frontend_recv_task)
t.start()

MAX_NAME_LEN = 20

cur_face = None
prev_face = None
face2greeting = {}
face2name = {}
cur_state_face = None
awaiting_name = False
awaiting_greeting = False
awaiting_change_confirmation = False

USE_MOCK_SPEECH_RECOGNITION = True

class MockSpeechRecognition():
    def setLanguage(self, language):
        self.language = language
    def setVocabulary(self, vocabulary, enableWordSpotting):
        self.vocabulary = vocabulary
        self.word_spotting = enableWordSpotting
    def subscribe(self, name):
        self.name = name
    def pause(self, p):
        self.paused = p
        

app = qi.Application(["App", "--qi-url=" + url ])
app.start() # non blocking
session = app.session
memory_service=app.session.service("ALMemory")

# FOR TTS
class TTSWrapper():
    def __init__(self, tts_service):
        self.tts_service = tts_service
    
    def say(self, text):
        print("Robot says:" + text)
        self.tts_service.say(text)
        
tts_service = session.service("ALTextToSpeech")
tts_service.setLanguage("English")
tts_service.setParameter("speed", 30)
tts_service = TTSWrapper(tts_service)

## FOR MOTION
# motion_service = session.service("ALMotion")
# for i in range(3):
#     motion_service.move(5, 5, 0)
#     time.sleep(3)
#     motion_service.stopMove()
#     motion_service.moveTo(0, 0, math.pi / 2)
#####

## FOR SPEECH RECOGNITION
def recognize_vocabulary(mem, vocabulary):
    global ASRKey
    global speech_recognition
    
    speech_recognition.pause(True)
    speech_recognition.setVocabulary(vocabulary, True)
    speech_recognition.pause(False)
    
    rec = mem.getData(ASRKey)
    if rec is not None:        
        rec = rec.lower()
        mem.insertData(ASRKey, None)
        if USE_MOCK_SPEECH_RECOGNITION:
            for v in speech_recognition.vocabulary:
                if v in rec:
                    return [v, rec]
        else:
            beg = rec.split('<')[1].split('>')[0]
            phrase = rec.split('>')[1].split('<')[0]
            end = rec.split('<')[-1].split('>')[0]
            return [phrase, beg + ' ' + phrase + ' ' + end]
    return None

if USE_MOCK_SPEECH_RECOGNITION:
    speech_recognition = MockSpeechRecognition()
    ASRKey = "FakeRobot/ASR"
else:
    speech_recognition = session.service("ALSpeechRecognition")
    ASRKey = "WordRecognized"
speech_recognition.setLanguage("English")
mem = session.service("ALMemory")
mem.subscribeToEvent(ASRKey, "ASR", ASRKey)

# Start the speech recognition engine with user Test_ASR
speech_recognition.subscribe("ASR")

# Run the recognition loop in parallel
def face_recognition():
    global cur_face
    global prev_face
    
    r = conn.recv(len("Face 0000"))
    prev_face = cur_face
    if "NO" in r:
        cur_face = None
        return
    cur_face = int(r.split(' ')[1])
    
def update_frontend_face():
    global face_to_delete
    global awaiting_change_confirmation
    global awaiting_greeting
    global awaiting_name
    
    if (cur_face is not None) and (cur_face in face2name):
        conn_frontend.sendall(("Id:%04d,Name:{0:<%d}" % (cur_face, MAX_NAME_LEN)).format(face2name[cur_face]))
    else:
        conn_frontend.sendall(" " * (MAX_NAME_LEN + 4 + 9))
    
    if face_to_delete is not None:
        if face_to_delete in face2name:
            face2name.pop(face_to_delete)
        if face_to_delete in face2greeting:
            face2greeting.pop(face_to_delete)
        awaiting_change_confirmation = False
        awaiting_greeting = False
        awaiting_name = False
        face_to_delete = None

# t = Thread(face_recognition, args = ())
# t.run()

while True:
    face_recognition()
    update_frontend_face()
    print(cur_face)
    
    if cur_face is None:
        if awaiting_name:
            tts_service.say("Hey, you left before telling me your name!")
        elif awaiting_greeting:
            tts_service.say("Hey, you left before telling me how you would like to be greeted!")
        elif awaiting_change_confirmation:
            tts_service.say("I'll take that as a now then...")
        
        awaiting_name = False
        awaiting_greeting = False
        awaiting_change_confirmation = False
    
    if cur_face is not None and prev_face != cur_face:
        print("DIFFERENT FACE!!!")
        awaiting_name = False
        awaiting_greeting = False
        awaiting_change_confirmation = False
        
        if cur_face not in face2name:
            tts_service.say("Hello, what is your name?")
            awaiting_name = True
        else:
            if cur_face not in face2greeting:
                tts_service.say("{}!. You have not set a greeting yet. How would you like to be greeted?".format(face2name[cur_face]))
                awaiting_greeting = True
            else:
                tts_service.say("{}, {}! Hope you are having a great day!".format(face2greeting[cur_face], face2name[cur_face]))
                tts_service.say("Would you like to change your greeting?")
                awaiting_change_confirmation = True
    
    if awaiting_name:
        rec = recognize_vocabulary(mem, ['my name is',
                                         'i am', 'i\'m',
                                         'i am called', 'i\'m called',
                                         'i am known as', 'i\'m known as',
                                         'i am named', 'i\'m named',
                                         'i go by'])
        if rec is not None:
            rec_phrase = rec[0]
            whole_phrase = rec[1]
            name = whole_phrase[whole_phrase.find(rec_phrase) + len(rec_phrase):].strip()
            name = name[:MAX_NAME_LEN]
            face2name[cur_face] = name
            tts_service.say("Say, {}, how would you like to be greeted?".format(name))
            awaiting_name = False
            awaiting_greeting = True

    if awaiting_greeting:
        rec = recognize_vocabulary(mem, ['with',
                                         'i would like to be greeted with',
                                         'i\'d like to be greeted using',
                                         'i\'d like to be greeted with'
                                         'i would like to be greeted as',
                                         'using',
                                         '']) # This might not work with the actual ASR
        if rec is not None:
            rec_phrase = rec[0]
            whole_phrase = rec[1]
            if rec_phrase == '':
                greeting = whole_phrase.strip()
            else:
                greeting = whole_phrase[whole_phrase.find(rec_phrase) + len(rec_phrase):].strip()
            face2greeting[cur_face] = greeting
            tts_service.say("Got it. {} will be greeted with {}.".format(face2name[cur_face], greeting))
            awaiting_greeting = False
            
    if awaiting_change_confirmation:
        rec = recognize_vocabulary(mem, ['yes', 'no', 'sure', 'okay', 'nope', 'no thanks', 'no thank you'])
        if rec is not None:
            if rec[0] == 'yes' or rec[0] == 'sure' or rec[0] == 'okay':
                tts_service.say("Then how else would you like to be greeted?")
                awaiting_greeting = True
            else:
                tts_service.say("Okay!")
            awaiting_change_confirmation = False

app.run() # blocking