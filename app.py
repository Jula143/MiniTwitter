from flask import Flask, render_template, request, redirect, url_for, session
import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from werkzeug.utils import secure_filename  # Import secure_filename for file uploads
import base64

app = Flask(__name__)
app.secret_key = '85093485204985320'  # Change this to a secret key

# Initialize the gRPC channel and stub
channel = grpc.insecure_channel('localhost:50051')
stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)

# Define the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def b64encode_filter(data):
    return base64.b64encode(data).decode('utf-8')

# Register the custom filter function in your Flask app
app.jinja_env.filters['b64encode'] = b64encode_filter

def send_message(message, username, file):
    current_time = Timestamp()
    current_time.GetCurrentTime()

    # Process the uploaded file (you may need to save it to your server)
    if file:
        file_data = file.read()
        file_name = secure_filename(file.filename)
        file_type = file.mimetype

        # Create a FileAttachment message to send with the text message
        file_attachment = minitwitter_pb2.FileAttachment(
            file_name=file_name,
            file_type=file_type,
            file_data=file_data
        )

        # Send the Message with the FileAttachment
        stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=current_time, file_attachment=file_attachment))
    else:
        # If no file was uploaded, send the message without a file attachment
        stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=current_time))

def get_messages(n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n))
    return response.messages

@app.route('/')
def home():
    num = request.args.get('num', default=10, type=int)
    messages = get_messages(num)
    return render_template('index.html', messages=messages)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    session['logged_in'] = True
    session['username'] = username
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/send', methods=['POST'])
def send():
    if 'logged_in' in session:
        username = session['username']
        message = request.form['message']
        file = request.files.get('file')  # Get the uploaded file

        send_message(message, username, file)

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
