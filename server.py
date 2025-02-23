import os
import json
import grpc
from concurrent import futures
import time
import re
import logging
import datetime
import hashlib

import chat_pb2
import chat_pb2_grpc

# ---------------------------
# Load configuration
# ---------------------------
with open("config.json", "r") as config_file:
    config = json.load(config_file)

HOST = config.get("server_host", "0.0.0.0")
PORT = config.get("server_port", 50051)

# ---------------------------
# Ensure logs folder exists
# ---------------------------
os.makedirs("logs", exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join("logs", f"chat_server_{timestamp}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.info("-------------------------------------------------")
logging.info("Chat Server started.")
logging.info(f"Logging to file: {log_filename}")

# ---------------------------
# In-memory storage for users.
# Each user is a dict with keys: "password" and "messages"
# "messages" is a list of dicts with keys: "from", "content", "read", "timestamp"
# ---------------------------
users_db = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class ChatService(chat_pb2_grpc.ChatServiceServicer):
    def CreateAccount(self, request, context):
        username = request.username
        password = request.password
        if not username or not password:
            return chat_pb2.CreateAccountResponse(message="Username or password missing", success=False)
        if username in users_db:
            return chat_pb2.CreateAccountResponse(message="Username already taken", success=False)
        users_db[username] = {"password": password, "messages": []}
        logging.info(f"Account created: {username}")
        return chat_pb2.CreateAccountResponse(message=f"Account '{username}' created successfully", success=True)

    def Login(self, request, context):
        username = request.username
        password = request.password
        if not username or not password:
            return chat_pb2.LoginResponse(message="Username or password missing", unread_count=0, success=False)
        if username not in users_db:
            return chat_pb2.LoginResponse(message="No such user", unread_count=0, success=False)
        if users_db[username]["password"] != password:
            return chat_pb2.LoginResponse(message="Incorrect password", unread_count=0, success=False)
        unread_count = sum(1 for m in users_db[username]["messages"] if not m.get("read", False))
        logging.info(f"User logged in: {username}")
        return chat_pb2.LoginResponse(
            message=f"User '{username}' logged in successfully",
            unread_count=unread_count,
            success=True
        )

    def ListAccounts(self, request, context):
        pattern = request.pattern
        all_users = list(users_db.keys())
        if pattern:
            matches = [u for u in all_users if re.search(pattern, u, re.IGNORECASE)]
        else:
            matches = all_users
        logging.info(f"Listing accounts with pattern: '{pattern}'")
        return chat_pb2.ListAccountsResponse(accounts=matches, success=True)

    def SendMessage(self, request, context):
        # Note: we renamed the field from "from" to "sender" in the proto.
        from_user = request.sender
        to_user = request.to
        content = request.content
        if not from_user or not to_user or content is None:
            return chat_pb2.SendMessageResponse(message="Missing fields", success=False)
        if from_user not in users_db:
            return chat_pb2.SendMessageResponse(message=f"Sender '{from_user}' does not exist", success=False)
        if to_user not in users_db:
            return chat_pb2.SendMessageResponse(message=f"Recipient '{to_user}' does not exist", success=False)
        timestamp_str = datetime.datetime.now().strftime('%m/%d %H:%M')
        users_db[to_user]["messages"].append({
            "from": from_user,
            "content": content,
            "read": False,
            "timestamp": timestamp_str
        })
        logging.info(f"Message from '{from_user}' to '{to_user}' sent")
        return chat_pb2.SendMessageResponse(message="Message sent successfully", success=True)

    def ReadNewMessages(self, request, context):
        username = request.username
        count = request.count
        if not username:
            return chat_pb2.ReadNewMessagesResponse(messages=[], success=False)
        if username not in users_db:
            return chat_pb2.ReadNewMessagesResponse(messages=[], success=False)
        all_messages = users_db[username]["messages"]
        unread = [m for m in all_messages if not m.get("read", False)]
        if count <= 0 or count > len(unread):
            count = len(unread)
        selected = unread[:count]
        for m in selected:
            m["read"] = True
        encoded = [f"{m['timestamp']} - From: {m['from']} - {m['content']}" for m in selected]
        logging.info(f"Read {len(encoded)} new messages for user '{username}'")
        return chat_pb2.ReadNewMessagesResponse(messages=encoded, success=True)

    def DeleteMessages(self, request, context):
        username = request.username
        msg_ids = request.message_ids  # list of ints; a single value -1 indicates "delete all"
        if not username or not msg_ids:
            return chat_pb2.DeleteMessagesResponse(message="Missing fields", success=False)
        if username not in users_db:
            return chat_pb2.DeleteMessagesResponse(message=f"User '{username}' does not exist", success=False)
        messages = users_db[username]["messages"]
        if len(msg_ids) == 1 and msg_ids[0] == -1:
            users_db[username]["messages"] = []
            logging.info(f"All messages deleted for user '{username}'")
            return chat_pb2.DeleteMessagesResponse(message="All messages deleted", success=True)
        # Delete messages using 1-indexed positions
        indices = sorted(msg_ids, reverse=True)
        deleted_count = 0
        for i in indices:
            idx = i - 1
            if 0 <= idx < len(messages):
                del messages[idx]
                deleted_count += 1
        logging.info(f"Deleted {deleted_count} messages for user '{username}'")
        return chat_pb2.DeleteMessagesResponse(message=f"Deleted {deleted_count} messages.", success=True)

    def DeleteAccount(self, request, context):
        username = request.username
        if not username:
            return chat_pb2.DeleteAccountResponse(message="Username missing", success=False)
        if username not in users_db:
            return chat_pb2.DeleteAccountResponse(message=f"No such user '{username}'", success=False)
        del users_db[username]
        logging.info(f"Account deleted: {username}")
        return chat_pb2.DeleteAccountResponse(message=f"Account '{username}' deleted.", success=True)

    def ListMessages(self, request, context):
        username = request.username
        if not username or username not in users_db:
            return chat_pb2.ListMessagesResponse(messages=[], success=False)
        messages = [m for m in users_db[username]["messages"] if m.get("read", False)]
        encoded = [f"{m['timestamp']} - From: {m['from']} - {m['content']}" for m in messages]
        logging.info(f"Listing all read messages for user '{username}'")
        return chat_pb2.ListMessagesResponse(messages=encoded, success=True)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatService(), server)
    bind_address = f"{HOST}:{PORT}"
    server.add_insecure_port(bind_address)
    server.start()
    print(f"Server started on {bind_address}")
    logging.info(f"Server listening on {bind_address}")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("Shutting down server")
        logging.info("Server shutting down (KeyboardInterrupt).")
        server.stop(0)

if __name__ == '__main__':
    serve()
