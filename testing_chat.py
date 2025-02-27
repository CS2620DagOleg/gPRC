import unittest
from unittest.mock import MagicMock
import re
import datetime

# Importing generated classes during application run 
import chat_pb2
import chat_pb2_grpc

# importing server code 
from server import ChatService, users_db, hash_password

class TestChatService(unittest.TestCase):

    #cleaning the database before each test
    def setUp(self):
        users_db.clear()
        self.service = ChatService()
        self.mock_context = MagicMock()

    #testing if account is created successfully
    def test_create_account_success(self):
        request = chat_pb2.CreateAccountRequest(
            username="alice",
            password=hash_password("secret123")
        )
        response = self.service.CreateAccount(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("created successfully", response.message.lower())
        self.assertIn("alice", users_db)

    #testing if duplicate accounts with the same username are not created
    def test_create_account_already_taken(self):
        users_db["bob"] = {"password": "somehashed", "messages": []}
        request = chat_pb2.CreateAccountRequest(
            username="bob",
            password=hash_password("secret123")
        )
        response = self.service.CreateAccount(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertIn("already taken", response.message.lower())

    #checking that if an account is created with missing fields, the creation fails
    def test_create_account_missing_fields(self):
        request = chat_pb2.CreateAccountRequest(username="", password="")
        response = self.service.CreateAccount(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertIn("missing", response.message.lower())

    #verifying that given correct credentials login is successful
    def test_login_success(self):
        users_db["charlie"] = {"password": hash_password("p@ss"), "messages": []}
        request = chat_pb2.LoginRequest(username="charlie", password=hash_password("p@ss"))
        response = self.service.Login(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("logged in successfully", response.message.lower())
        self.assertEqual(response.unread_count, 0)

    #checking failure on incorrect password
    def test_login_incorrect_password(self):
        users_db["charlie"] = {"password": hash_password("p@ss"), "messages": []}
        request = chat_pb2.LoginRequest(username="charlie", password=hash_password("wrong"))
        response = self.service.Login(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertIn("incorrect password", response.message.lower())

    #checks the users retrieved are as expected
    def test_list_accounts(self):
        users_db["alice"] = {"password": "pw1", "messages": []}
        users_db["alex"] = {"password": "pw2", "messages": []}
        users_db["bob"] = {"password": "pw3", "messages": []}

        request = chat_pb2.ListAccountsRequest(username="", pattern="al")
        response = self.service.ListAccounts(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertEqual(sorted(response.accounts), ["alex", "alice"])

    #checking if message is sent successfully
    def test_send_message_success(self):
        users_db["alice"] = {"password": "pw", "messages": []}
        users_db["bob"] = {"password": "pw", "messages": []}
        request = chat_pb2.SendMessageRequest(sender="alice", to="bob", content="Hello Bob!")
        response = self.service.SendMessage(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("message sent successfully", response.message.lower())
        self.assertEqual(len(users_db["bob"]["messages"]), 1)
        self.assertEqual(users_db["bob"]["messages"][0]["from"], "alice")

    #if sender or receiver is missing, message sending should fail
    def test_send_message_missing_fields(self):
        request = chat_pb2.SendMessageRequest(sender="", to="", content="")
        response = self.service.SendMessage(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertIn("missing fields", response.message.lower())

    #if a user does not exist in the database, message sending should fail
    def test_send_message_unknown_sender(self):
        users_db["bob"] = {"password": "pw", "messages": []}
        request = chat_pb2.SendMessageRequest(sender="alice", to="bob", content="Hello?")
        response = self.service.SendMessage(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertIn("does not exist", response.message.lower())

    #checks if a specified number of messages can be read
    def test_read_new_messages(self):
        users_db["alice"] = {
            "password": "pw",
            "messages": [
                {"from": "bob", "content": "Hello", "read": False, "timestamp": "01/01 12:00"},
                {"from": "carol", "content": "Hi", "read": False, "timestamp": "01/01 12:05"}
            ]
        }
        request = chat_pb2.ReadNewMessagesRequest(username="alice", count=1)
        response = self.service.ReadNewMessages(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertEqual(len(response.messages), 1)
        self.assertTrue(users_db["alice"]["messages"][0]["read"])
        self.assertFalse(users_db["alice"]["messages"][1]["read"])

    #checks if all messages can be read
    def test_read_new_messages_all(self):
        users_db["alice"] = {
            "password": "pw",
            "messages": [
                {"from": "bob", "content": "Hello", "read": False, "timestamp": "01/01 12:00"},
                {"from": "carol", "content": "Hi", "read": False, "timestamp": "01/01 12:05"}
            ]
        }
        request = chat_pb2.ReadNewMessagesRequest(username="alice", count=0)  # 0 = read all
        response = self.service.ReadNewMessages(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertEqual(len(response.messages), 2)
        self.assertTrue(users_db["alice"]["messages"][0]["read"])
        self.assertTrue(users_db["alice"]["messages"][1]["read"])

    #checks if messages can be deleted
    def test_delete_messages(self):
        users_db["alice"] = {
            "password": "pw",
            "messages": [
                {"from": "bob", "content": "M1", "read": True, "timestamp": "01/01 12:00"},
                {"from": "carol", "content": "M2", "read": True, "timestamp": "01/01 12:05"}
            ]
        }
        request = chat_pb2.DeleteMessagesRequest(username="alice", message_ids=[1])
        response = self.service.DeleteMessages(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("deleted 1 messages", response.message.lower())
        self.assertEqual(len(users_db["alice"]["messages"]), 1)
        self.assertEqual(users_db["alice"]["messages"][0]["content"], "M2")

    #checks if all messages can be deleted
    def test_delete_all_messages(self):
        users_db["alice"] = {
            "password": "pw",
            "messages": [
                {"from": "bob", "content": "M1", "read": True, "timestamp": "01/01 12:00"},
                {"from": "carol", "content": "M2", "read": True, "timestamp": "01/01 12:05"}
            ]
        }
        request = chat_pb2.DeleteMessagesRequest(username="alice", message_ids=[-1])  # -1 => delete all
        response = self.service.DeleteMessages(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("all messages deleted", response.message.lower())
        self.assertEqual(len(users_db["alice"]["messages"]), 0)

    #checks if account can be deleted
    def test_delete_account(self):
        users_db["alice"] = {"password": "pw", "messages": []}
        request = chat_pb2.DeleteAccountRequest(username="alice")
        response = self.service.DeleteAccount(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertIn("account 'alice' deleted", response.message.lower())
        self.assertNotIn("alice", users_db)

    #checks if read messages can be listed
    def test_list_messages(self):
        users_db["alice"] = {
            "password": "pw",
            "messages": [
                {"from": "bob", "content": "M1", "read": True, "timestamp": "01/01 12:00"},
                {"from": "carol", "content": "M2", "read": False, "timestamp": "01/01 12:05"}
            ]
        }
        request = chat_pb2.ListMessagesRequest(username="alice")
        response = self.service.ListMessages(request, self.mock_context)
        self.assertTrue(response.success)
        self.assertEqual(len(response.messages), 1)
        self.assertIn("m1", response.messages[0].lower())

    #checks if messages can be listed for an unknown user
    def test_list_messages_unknown_user(self):
        request = chat_pb2.ListMessagesRequest(username="nonexistent")
        response = self.service.ListMessages(request, self.mock_context)
        self.assertFalse(response.success)
        self.assertEqual(len(response.messages), 0)

if __name__ == '__main__':
    unittest.main()
