import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc

def send_message(stub, message, username):
    stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username))

def get_messages(stub, n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n))
    return response.messages

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)
    
    username = input("Enter username: ")
    
    while(True):
        message = input("Enter message: ") 
        send_message(stub, message, username)
        
        num = input("How many messages do you want to see: ") 
        messages = get_messages(stub, int(num))
        print("Latest Messages:")
        for message in messages:
            print(message.text)


if __name__ == '__main__':
    run()