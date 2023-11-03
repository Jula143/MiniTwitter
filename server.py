import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from concurrent import futures

class MiniTwitterServicer(minitwitter_pb2_grpc.MiniTwitterServicer):
    def __init__(self):
        self.messages = []

    def SendMessage(self, request, context):
        self.messages.append(request)
        return minitwitter_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

    def GetMessages(self, request, context):
        response = minitwitter_pb2.GetMessagesResponse(messages=self.messages[-request.n:])
        return response

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    minitwitter_pb2_grpc.add_MiniTwitterServicer_to_server(MiniTwitterServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()