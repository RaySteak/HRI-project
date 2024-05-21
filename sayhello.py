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
pip = os.getenv('PEPPER_IP')
pport = 40369
url = "tcp://" + pip + ":" + str(pport)

kTopCamera = 0
kBottomCamera = 1
kDepthCamera = 2
kStereoCamera = 3

used_camera = kTopCamera

USE_MOCK_SPEECH_RECOGNITION = True

class MockSpeechRecognition():
    def setLanguage(self, language):
        self.language = language
    def setVocabulary(self, vocabulary, enableWordSpotting):
        self.vocabulary = vocabulary
        self.word_spotting = enableWordSpotting
    def subscribe(self, name):
        self.name = name

app = qi.Application(["App", "--qi-url=" + url ])
app.start() # non blocking
session = app.session
memory_service=app.session.service("ALMemory")

# FOR TTS
tts_service = session.service("ALTextToSpeech")
tts_service.setLanguage("English")
tts_service.setParameter("speed", 90)
tts_service.say("Hello. How are you?")

## FOR MOTION
# motion_service = session.service("ALMotion")
# for i in range(3):
#     motion_service.move(5, 5, 0)
#     time.sleep(3)
#     motion_service.stopMove()
#     motion_service.moveTo(0, 0, math.pi / 2)
#####
if USE_MOCK_SPEECH_RECOGNITION:
    speech_recognition = MockSpeechRecognition()
else:
    speech_recognition = session.service("ALSpeechRecognition")
speech_recognition.setLanguage("English")
mem = session.service("ALMemory")
mem.subscribeToEvent("WordRecognized", "Test_ASR", "WordRecognized")

vocabulary = ['yes', 'no', 'hello', 'goodbye']
speech_recognition.setVocabulary(vocabulary, True)
# Start the speech recognition engine with user Test_ASR
speech_recognition.subscribe("Test_ASR")


# FOR VIDEO
video_service = session.service("ALVideoDevice")
# video_service.setResolution("python_client", 2)
# video_service.setFrameRate(30)
# video_service.setActiveCamera(0)
# video_service.subscribeCamera("python_client", 0, 1, 11, 5)

print("Expected image parameters:")
params = video_service.getExpectedImageParameters(used_camera)
if params is not None:
    width = params[0][0]
    height = params[0][1]
    print(width, height)
else:
    width = 640
    height = 480
    print("No params...")

# Get image from disk
img = Image.open("photo.jpg").resize((width, height), resample = Image.BICUBIC)
img = np.array(img)
img = (img * 255).astype(np.uint8)
print(len(img.flatten().tolist()))

# Put image in video_service
print("Putting image in video_service")
ret = video_service.putImage(used_camera, 640, 480, img.flatten().tolist())
print("Put image, ret: {}".format(ret))


while True:
    rec = mem.getData("WordRecognized")
    if rec is not None:
        print(rec)

app.run() # blocking