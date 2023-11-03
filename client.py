import grpc
import minitwitter_pb2
import minitwitter_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime



def send_message(stub, message, username, current_time):
    stub.SendMessage(minitwitter_pb2.Message(text=message, sender=username, creation_time=current_time))

def get_messages(stub, n):
    response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=n))
    return response.messages

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)


    username = input("Enter username: ")
    
    while(True):
        message = input("Enter message: ") 
        
        current_time = Timestamp()
        current_time.GetCurrentTime()
        

        send_message(stub, message, username, current_time)

        
        num = input("How many messages do you want to see: ") 
        messages = get_messages(stub, int(num))
        print("Latest Messages:")
        for message in messages:
            # Convert Timestamp to a human-readable format
            creation_time = datetime.fromtimestamp(message.creation_time.ToNanoseconds() / 1e9)
            formatted_time = creation_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Print current time in hours and minutes, sender, and text
            print(f"[{formatted_time}] {message.sender}: {message.text}")
            


if __name__ == '__main__':
    run()