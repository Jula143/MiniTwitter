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
            response_message = minitwitter_pb2.Message(
                text=message["text"],
                sender=message["sender"],
                creation_time=message["creation_time"],
            )

            if "file_attachment" in message:
                file_attachment = message["file_attachment"]
                if "file_name" in file_attachment and "file_data_id" in file_attachment and "file_type" in file_attachment:
                    file_data_id = ObjectId(file_attachment["file_data_id"])
                    file_data = fs.get(file_data_id).read()
                    response_message.file_attachment.CopyFrom(minitwitter_pb2.FileAttachment(
                        file_name=file_attachment["file_name"],
                        file_data=file_data,
                        file_type=file_attachment["file_type"]
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
            return minitwitter_pb2.FileAttachment(file_data=file_data, file_type=file_type)
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Attachment not found")
            return minitwitter_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    minitwitter_pb2_grpc.add_MiniTwitterServicer_to_server(MiniTwitterServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
