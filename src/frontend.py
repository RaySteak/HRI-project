from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit
from threading import Thread
import socket


PORT = 5000
GREETINGS_IP = '127.0.0.1'
GREETINGS_PORT = 12345

MAX_NAME_LEN = 20

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((GREETINGS_IP, GREETINGS_PORT))

s.sendall('i'.encode())

id_in_view = None
name_in_view = None

app = Flask(__name__)
socketio = SocketIO(app, debug = True, cors_allowed_origins = '*')

def greetings_module_handler():
    global face_in_view
    while True:
        r = s.recv(len('Id:0000,Name:' + ' ' * MAX_NAME_LEN)).decode()
        id, name = None, None
        if r.startswith('Id:'):
            id = int(r[len('Id:'):len('Id:0000')].strip())
            name = r[len('Id:0000,Name:'):].strip()
        id_in_view, name_in_view = id, name
        if name_in_view != None:
            socketio.emit('face_in_view', {'name': name_in_view, 'id': id_in_view})
        else:
            socketio.emit('face_in_view', {})
            
t = Thread(target = greetings_module_handler)
t.start()

@app.route('/', methods = ['GET'])
def index():
    return render_template('delete_user.html')

@socketio.on('delete_user')
def delete_user(id):
    s.sendall(('D' + str(id)).encode())

if __name__ == '__main__':
    app.run(host = '0.0.0.0', threaded = True, port = PORT)