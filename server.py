import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from concurrent import futures
import pymongo
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
from google.protobuf.json_format import MessageToDict

client = MongoClient("mongodb://localhost:27017/")
db = client["minitwitter"]
fs = GridFS(db, collection="file_attachments")

class MiniTwitterServicer(minitwitter_pb2_grpc.MiniTwitterServicer):
    def __init__(self):
        self.messages = []
        self.likes = {} 
        self.comments = {}

    def SendMessage(self, request, context):
        message_id = request.message_id
        message = request.text
        sender = request.sender
        creation_time = request.creation_time
        file_attachment = request.file_attachment

        if file_attachment:
            file_id = fs.put(file_attachment.file_data, filename=file_attachment.file_name, content_type=file_attachment.file_type)
            file_data_id = ObjectId(file_id)
            file_attachment = minitwitter_pb2.FileAttachment(
                file_name=file_attachment.file_name,
                file_type=file_attachment.file_type,
                file_data_id=str(file_data_id)
            )
        else:
            file_data_id = None

        db.messages.insert_one({
            "message_id": message_id, 
            "text": message,
            "sender": sender,
            "creation_time": creation_time,
            "file_attachment": MessageToDict(file_attachment) if file_attachment else None
        })

        return minitwitter_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

    def GetMessages(self, request, context):
        client = MongoClient("mongodb://localhost:27017")
        db = client["minitwitter"]
        collection = db["messages"]

        messages = collection.find().sort("creation_time", -1).limit(request.n)
        response_messages = []
        

        for message in messages:
            likes_count = db.likes.count_documents({"message_id": message["message_id"]})
            response_message = minitwitter_pb2.Message(
                message_id=message["message_id"],
                text=message["text"],
                sender=message["sender"],
                creation_time=message["creation_time"],
                likes=likes_count,
            )

            if "file_attachment" in message:
                file_attachment = message["file_attachment"]
                if "fileName" in file_attachment and "fileDataId" in file_attachment and "fileType" in file_attachment:
                    file_data_id = ObjectId(file_attachment["fileDataId"])
                    file_data = fs.get(file_data_id).read()
                    response_message.file_attachment.CopyFrom(minitwitter_pb2.FileAttachment(
                        file_name=file_attachment["fileName"],
                        file_data=file_data,
                        file_type=file_attachment["fileType"],
                        file_data_id=str(file_data_id)
                    ))
                response_messages.append(response_message)

        response = minitwitter_pb2.GetMessagesResponse(messages=response_messages)
        client.close()
        return response

    def GetAttachment(self, request, context):
        attachment_id = request.attachment_id
        attachment = fs.get(ObjectId(attachment_id))
        if attachment:
            file_data = attachment.read()
            file_type = attachment.content_type
            print("Attachment found")
            attachmentv2 = minitwitter_pb2.FileAttachment(
                file_name=attachment.filename,
                file_type=file_type,
                file_data=bytes(file_data),
                file_data_id=attachment_id
            )
            return minitwitter_pb2.GetAttachmentsResponse(attachments=attachmentv2)
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Attachment not found")
            print("Attachement not found")
            return minitwitter_pb2.google_dot_protobuf_dot_empty__pb2.Empty()
        
    def AddLike(self, request, context):
        message_id = request.message_id
        username = request.username


        if db.likes.find_one({"message_id": message_id, "username": username}) != None:
            db.likes.delete_one({"message_id": message_id, "username": username})
        else:
            db.likes.insert_one({"message_id": message_id, "username": username})


        return minitwitter_pb2.AddLikeResponse()


    def AddComment(self, request, context):
        message_id = request.message_id
        username = request.username
        text = request.text

        comment = minitwitter_pb2.Comment(username=username, text=text)

        #add comment to db
        db.comments.insert_one({"message_id": message_id, "username": username, "text": text})

        return minitwitter_pb2.google_dot_protobuf_dot_empty__pb2.Empty()
    
    def GetLikes(self, request, context):
        username = request.username

        likes_collection = db.likes

        liked_messages = likes_collection.find({"username": username}, {"message_id": 1})

        liked_message_ids = [like["message_id"] for like in liked_messages]

        return minitwitter_pb2.GetLikesResponse(liked_message_ids=liked_message_ids)
    
    def GetComments(self, request, context):
        message_id = request.message_id

        comments_collection = db.comments

        comments = comments_collection.find({"message_id": message_id})

        response_comments = []

        for comment in comments:
            response_comment = minitwitter_pb2.Comment(
                username=comment["username"],
                text=comment["text"]
            )
            response_comments.append(response_comment)

        return minitwitter_pb2.GetCommentsResponse(comments=response_comments)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    minitwitter_pb2_grpc.add_MiniTwitterServicer_to_server(MiniTwitterServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
