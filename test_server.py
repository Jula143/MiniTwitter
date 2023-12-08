import unittest
from flask import Flask
from flask_testing import TestCase
from app import app, send_message
import unittest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from grpc.aio import Channel, UnaryUnaryMultiCallable
from grpc import aio
import minitwitter_pb2
import minitwitter_pb2_grpc
from  server import MiniTwitterServicer
from google.protobuf.timestamp_pb2 import Timestamp
import datetime
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["minitwitter"]
import unittest
import grpc
from app import app, send_message
# from your_proto_file import minitwitter_pb2, minitwitter_pb2_grpc
from concurrent import futures
import uuid
# mongo = PyMongo(app)

class TestServer(TestCase):

    def create_app(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    async def asyncSetUp(self):
        self.server = aio.server(ThreadPoolExecutor())
        minitwitter_pb2_grpc.add_MiniTwitterServicer_to_server(MiniTwitterServicer(), self.server)
        port = self.server.add_insecure_port('[::]:50051')
        self.server.start()
        self.channel = aio.insecure_channel(f'localhost:{port}')

    async def asyncTearDown(self):
        await self.server.stop(0)
        await self.channel.close()

    def test_send_message_and_get_messages(self):
        with app.test_request_context():
            message_text = "Mniam mniam!"
            sender = "Zygzak mcqueen"
            file_attachment = None

            send_message(message_text, sender, file_attachment)

            with grpc.insecure_channel('localhost:50051') as channel:
                stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)
                response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=1, username=sender))
                stored_message = response.messages[0]

            self.assertEqual(stored_message.text, message_text)
            self.assertEqual(stored_message.sender, sender)

    def test_add_like_and_get_likes(self):
        with app.test_request_context():
            sender = "Zygzak McQueen"
            message_text = "Mniam mniam!"
            file_attachment = None

            send_message(message_text, sender, file_attachment)

            with grpc.insecure_channel('localhost:50051') as channel:
                stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)
                response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=1, username=sender))
                stored_message = response.messages[0]
                message_id = stored_message.message_id

                response_like = stub.AddLike(minitwitter_pb2.AddLikeRequest(message_id=message_id, username=sender))
                self.assertIsNotNone(response_like)

                response_likes = stub.GetLikes(minitwitter_pb2.GetLikesRequest(username=sender))
                liked_message_ids = response_likes.liked_message_ids
                self.assertIn(message_id, liked_message_ids)

    def test_add_comment_and_get_comments(self):
        with app.test_request_context():
            sender = "Zygzak McQueen"
            message_text = "Mniam mniam!"
            file_attachment = None

            send_message(message_text, sender, file_attachment)

            with grpc.insecure_channel('localhost:50051') as channel:
                stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)

                response = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=1, username=sender))
                stored_message = response.messages[0]
                message_id = stored_message.message_id

                comment_text = "zjadlbym olej"
                stub.AddComment(
                    minitwitter_pb2.AddCommentRequest(message_id=message_id, username=sender, text=comment_text))

                response_comments = stub.GetComments(minitwitter_pb2.GetCommentsRequest(message_id=message_id))
                comments = response_comments.comments

                self.assertEqual(len(comments), 1)
                self.assertEqual(comments[0].text, comment_text)

    def test_like_and_comment_with_multiple_users(self):
        with app.test_request_context():
            user_one = "Zygzak McQueen"
            user_two = "Zlomek"
            message_text = "Mniam mniam!"
            file_attachment = None

            send_message(message_text, user_one, file_attachment)

            with grpc.insecure_channel('localhost:50051') as channel:
                stub = minitwitter_pb2_grpc.MiniTwitterStub(channel)
                response_messages = stub.GetMessages(minitwitter_pb2.GetMessagesRequest(n=1, username=user_one))
                message_id = response_messages.messages[0].message_id
                stub.AddLike(minitwitter_pb2.AddLikeRequest(message_id=message_id, username=user_two))

                comment_text = "Dobry olej!"
                stub.AddComment(
                    minitwitter_pb2.AddCommentRequest(message_id=message_id, username=user_two, text=comment_text))

                response_likes = stub.GetLikes(minitwitter_pb2.GetLikesRequest(username=user_two))
                liked_message_ids = response_likes.liked_message_ids

                response_comments = stub.GetComments(minitwitter_pb2.GetCommentsRequest(message_id=message_id))
                comments = response_comments.comments

                self.assertTrue(message_id in liked_message_ids)
                self.assertEqual(len(comments), 1)
                self.assertEqual(comments[0].text, comment_text)

if __name__ == '__main__':
    unittest.main()
