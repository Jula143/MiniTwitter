from flask import Flask, render_template, request, redirect, url_for
import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp

app = Flask(__name__)

# Initialize the gRPC channel and stub
channel = grpc.insecure_channel('localhost:50051')
stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)

def send_message(message, username):
    current_time = Timestamp()
    current_time.GetCurrentTime()
    stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=current_time))

def get_messages(n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n))
    return response.messages

@app.route('/')
def home():
    num = request.args.get('num', default=10, type=int)
    messages = get_messages(num)
    return render_template('index.html', messages=messages)

@app.route('/send', methods=['POST'])
def send():
    username = request.form['username']
    message = request.form['message']
    send_message(message, username)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
