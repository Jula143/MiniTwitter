from flask import Flask, render_template, request, redirect, url_for, session, Response, make_response, jsonify, flash
import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from werkzeug.utils import secure_filename
import base64
from flask_pymongo import PyMongo
import datetime
import uuid

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
    message_id = str(uuid.uuid4())
    if file:
        file_data = file.read()
        file_name = secure_filename(file.filename)
        file_type = file.mimetype
        file_attachment = minitwitter_pb2.FileAttachment(
            file_name=file_name,
            file_type=file_type,
            file_data=file_data
        )
        stub.SendMessage(minitwitter_pb2.Message(message_id=message_id, text=message, sender=username, creation_time=str(current_time), file_attachment=file_attachment))
    else:
        stub.SendMessage(minitwitter_pb2.Message(message_id=message_id, text=message, sender=username, creation_time=str(current_time)))

def get_messages(n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n, username=session.get('username', '')))
    messages = response.messages
    liked_messages = stub.GetLikes(minitwitter_pb2.GetLikesRequest(username=session.get('username', ''))).liked_message_ids
    
    for message in messages:
        timestamp_str = message.creation_time
        timestamp = datetime.datetime.fromtimestamp(int(float(timestamp_str)))
        message.creation_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        message.liked_by_user = message.message_id in liked_messages
        comments_response = stub.GetComments(minitwitter_pb2.GetCommentsRequest(message_id=message.message_id))
        comments = comments_response.comments
        message.comments.extend(reversed(comments))
    return messages

def add_like(message_id):
    stub.AddLike(minitwitter_pb2.AddLikeRequest(message_id=message_id, username=session['username']))

    return minitwitter_pb2.AddLikeResponse()

def add_comment(message_id, text):
    stub.AddComment(minitwitter_pb2.AddCommentRequest(
        message_id=message_id,
        username=session['username'],
        text=text
    ))

@app.route('/like/<message_id>')
def like(message_id):
    add_like(message_id)
    num = request.args.get('num', default=10, type=int)
    messages = get_messages(num)
    updated_message = next((message for message in messages if message.message_id == message_id), None)
    

    return jsonify({"message_id": message_id, "likes": updated_message.likes, "liked_by_user": updated_message.liked_by_user})

@app.route('/comment/<message_id>', methods=['POST'])
def comment(message_id):
    text = request.form['comment_text']
    add_comment(message_id, text)
    num = request.args.get('num', default=10, type=int)
    messages = get_messages(num)
    updated_message = next((message for message in messages if message.message_id == message_id), None)
    comments_list = [{"username": comment.username, "text": comment.text} for comment in updated_message.comments]
    #reverse list so that newest comments are at the top
    return jsonify({"message_id":updated_message.message_id, "comments": comments_list})

@app.route('/attachments/<attachment_id>')
def serve_attachment(attachment_id):
    attachment = stub.GetAttachment(minitwitter_pb2.GetAttachmentsRequest(attachment_id=attachment_id))
    attachment = attachment.attachments
    
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
    password = request.form['password']
    if mongo.db.users.find_one({"username": username, "password": password}) == None:
        session['logged_in'] = False
        return redirect(url_for('home'))
    else:
        session['logged_in'] = True
        session['username'] = username
        online_users.add(username)
    return redirect(url_for('home'))

def register_user(username, password, profile_picture):
    if profile_picture:
        profile_picture_data = profile_picture.read()
        profile_picture_name = secure_filename(profile_picture.filename)
        profile_picture_type = profile_picture.mimetype
        profile_picture_attachment = minitwitter_pb2.FileAttachment(
            file_name=profile_picture_name,
            file_type=profile_picture_type,
            file_data=profile_picture_data
        )
        stub.Register(minitwitter_pb2.RegisterRequest(username=username, password=password, profile_picture=profile_picture_attachment))
        session['logged_in'] = True
        session['username'] = username
        online_users.add(username)
    else:
        stub.Register(minitwitter_pb2.RegisterRequest(username=username, password=password))
        session['logged_in'] = True
        session['username'] = username
        online_users.add(username)
    return redirect(url_for('home'))

@app.route('/profile_picture/<username>')
def get_profile_picture(username):
    profile_picture = stub.GetProfile(minitwitter_pb2.ProfilePictureRequest(username=username))
    profile_picture = profile_picture.profile_picture
    if not profile_picture:
        print(404)
    response = make_response(profile_picture.file_data)
    response.headers["Content-Type"] = profile_picture.file_type
    return response


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    #check if user in database
    if mongo.db.users.find_one({"username": username}) != None:
        #write user already exists message
        flash('You are already registered, please log in')
        return render_template('index.html')
    profile_picture = request.files.get('profile_picture')
    
    if password == confirm_password:
        register_user(username, password, profile_picture)
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    username = session.get('username')
    if username in online_users:
        online_users.remove(username)
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/profile=<username>')
def load_profile(username):
    #find user in database
    user = mongo.db.users.find_one({"username": username})
    #load profile page
    return render_template('profile.html', username=username)
@app.route('/send', methods=['POST'])
def send():
    if 'logged_in' in session:
        username = session['username']
        message = request.form['message']
        file = request.files.get('file')
        send_message(message, username, file)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
