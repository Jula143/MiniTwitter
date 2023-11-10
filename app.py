from flask import Flask, render_template, request, redirect, url_for, session, Response, make_response
import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from werkzeug.utils import secure_filename
import base64
from flask_pymongo import PyMongo
import datetime

app = Flask(__name__)
app.secret_key = '85093485204985320'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/minitwitter'
mongo = PyMongo(app)

channel = grpc.insecure_channel('localhost:50051')
stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)


def b64encode_filter(data):
    return base64.b64encode(data).decode('utf-8')

app.jinja_env.filters['b64encode'] = b64encode_filter

online_users = set()

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            yield f"data: {len(online_users)}\n\n"
    return Response(event_stream(), content_type="text/event-stream")

def send_message(message, username, file):
    time_is = datetime.datetime.now()
    current_time = time_is.timestamp()
    if file:
        file_data = file.read()
        file_name = secure_filename(file.filename)
        file_type = file.mimetype
        file_attachment = minitwitter_pb2.FileAttachment(
            file_name=file_name,
            file_type=file_type,
            file_data=file_data
        )
        stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=str(current_time), file_attachment=file_attachment))
    else:
        stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=str(current_time)))

def get_messages(n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n))
    messages = response.messages
    for message in messages:
        print("attachment_id: ", message.file_attachment)
        timestamp_str = message.creation_time
        timestamp = datetime.datetime.fromtimestamp(int(float(timestamp_str)))
        message.creation_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return messages

@app.route('/attachments/<attachment_id>')
def serve_attachment(attachment_id):
    attachment = stub.GetAttachment(minitwitter_pb2.GetAttachmentsRequest(attachment_id=attachment_id))
    attachment = attachment.attachments
    print(attachment)
    
    if not attachment:
        print(404)
    response = make_response(attachment.file_data)
    response.headers["Content-Type"] = attachment.file_type
    return response

@app.route('/')
def home():
    num = request.args.get('num', default=10, type=int)
    messages = get_messages(num)
    return render_template('index.html', messages=messages, user_count=len(online_users))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    session['logged_in'] = True
    session['username'] = username
    online_users.add(username)
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    username = session.get('username')
    if username in online_users:
        online_users.remove(username)
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/send', methods=['POST'])
def send():
    if 'logged_in' in session:
        username = session['username']
        message = request.form['message']
        file = request.files.get('file')
        send_message(message, username, file)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
