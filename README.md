# ChatApp Documentation (gRPC Implementation)

This document provides a guide for our Chat Client/Server application implemented in Python with gRPC. Unlike previous versions that offered custom-delimited or JSON-based protocols, this implementation uses **gRPC** to handle all communications between the client and server. The gRPC approach offers a strongly typed API, automatic code generation from a `.proto` file, and built-in support for asynchronous calls and error handling.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture and Flow](#architecture-and-flow)
4. [Installation and Setup](#installation-and-setup)
5. [Usage Examples](#usage-examples)
6. [Proto File Overview](#proto-file-overview)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Potential Improvements](#potential-improvements)
10. [License](#license)

---

## 1. Overview

This **Chat Application** uses **gRPC** to facilitate communication between a multi-threaded Python server and a Tkinter-based client. Key points include:

- **Server**:
  - Manages user accounts (username, hashed password).
  - Stores and retrieves messages (both unread and read).
  - Exposes functionality (e.g. create account, login, send message, etc.) via gRPC RPC methods.

- **Client**:
  - Provides a graphical user interface using **Tkinter**.
  - Uses a gRPC channel and stub to make RPC calls to the server.
  - Allows users to create accounts, log in, send messages, read or list messages, delete messages, and delete accounts.

- **API Definition**:
  - The API is defined using **Protocol Buffers** in a `.proto` file.
  - Code is automatically generated (using `grpcio-tools`) to implement both client and server stubs.

---

## 2. Features

1. **Account Management**
   - **Create Account**: Register with a username and a hashed password.
   - **Login**: Verify credentials and retrieve the count of unread messages.
   - **Delete Account**: Remove the user and all associated messages.

2. **Messaging**
   - **Send Message**: Transmit a text message from one user to another.
   - **Read New Messages**: Retrieve unread messages (which are then marked as read).
   - **List All Messages**: Retrieve a list of previously read messages.
   - **Delete Messages**: Remove individual messages (by 1-indexed ID) or all messages at once.

3. **Listing Accounts**
   - Request a list of all user accounts, with an optional regex pattern for filtering (e.g. users starting with "A").
  
   
---

## 3. Architecture and Flow

### Server

- **gRPC Server**: Listens on a specified TCP port (e.g. `0.0.0.0:50051`).
- **Thread Pool**: Each RPC call is handled by a thread from a pool (via gRPC's built-in threading).
- **In-Memory Database**: Uses a dictionary (`users_db`) to store user data and messages.
- **Logging**: Major events (connections, account changes, message transfers) are logged.

### Client

- **Tkinter GUI**: Provides a user-friendly interface for interacting with the server.
- **gRPC Channel and Stub**: Establishes a channel to the server and calls RPC methods defined in the proto file.
- **State Management**: Maintains the currently logged-in user and reflects changes in the GUI.

### Data Flow

1. **API Call**:  
   The client creates a request (e.g. `LoginRequest`, `SendMessageRequest`) that is sent over the gRPC channel.

2. **Server Processing**:  
   The server decodes the request, performs business logic (e.g. updating `users_db`), and returns a response (e.g. `LoginResponse`).

3. **Response Handling**:  
   The client processes the response and updates the GUI accordingly.

---

## 4. Installation and Setup

### Requirements

- Python 3.7+
- gRPC libraries: Install via:
  ```bash
  pip install grpcio grpcio-tools
  ```
- Tkinter (typically preinstalled on Windows/macOS; on Linux, use `sudo apt-get install python3-tk`).

### Obtaining the Code

- Place the server script (e.g. `chat_server.py`) and client script (e.g. `chat_client.py`) in the same directory.
- Ensure the generated gRPC modules (`chat_pb2.py` and `chat_pb2_grpc.py`) are present (generated from the provided proto file).

### Running the Server

```bash
python chat_server.py
```

- Adjust the host/port in `config.json` if necessary.

### Running the Client

```bash
python chat_client.py
```

- A GUI window will open. Adjust `config.json` if connecting to a server on a different IP or port.
- Client logs are written to `logs/chat_client_<timestamp>.log`.

---

## 5. Usage Examples

### Common User Actions via the GUI

1. **Create Account**
   - Select "Create Account" and enter a new username and password.
   - On success, a confirmation message is displayed.

2. **Login**
   - Enter your credentials on the "Login" screen.
   - Upon successful login, the user is informed of the number of unread messages.

3. **Send Message**
   - Choose a recipient, enter a message, and send it.
   - The server checks that both the sender and recipient exist before storing the message.

4. **Read New Messages**
   - Specify the number of new messages to read (or leave blank to read all).
   - Retrieved messages are marked as read on the server.

5. **List Accounts**
   - Provide an optional regex pattern to filter accounts.
   - The list of matching accounts is returned and displayed.

6. **Delete Account**
   - Confirm deletion to remove your account and all associated messages from the server.

7. **Delete Messages**
   - In the "Show All Messages" window, select individual messages (using checkboxes) or choose to delete all messages by sending a special value.

---

## 6. Proto File Overview

The gRPC API is defined using Protocol Buffers. The `.proto` file outlines all the request and response messages and the RPC methods available in the `ChatService`. For example:

```proto
syntax = "proto3";

package chat;

service ChatService {
  rpc CreateAccount(CreateAccountRequest) returns (CreateAccountResponse);
  rpc Login(LoginRequest) returns (LoginResponse);
  rpc ListAccounts(ListAccountsRequest) returns (ListAccountsResponse);
  rpc SendMessage(SendMessageRequest) returns (SendMessageResponse);
  rpc ReadNewMessages(ReadNewMessagesRequest) returns (ReadNewMessagesResponse);
  rpc DeleteMessages(DeleteMessagesRequest) returns (DeleteMessagesResponse);
  rpc DeleteAccount(DeleteAccountRequest) returns (DeleteAccountResponse);
  rpc ListMessages(ListMessagesRequest) returns (ListMessagesResponse);
}

message CreateAccountRequest { string username = 1; string password = 2; }
message CreateAccountResponse { string message = 1; bool success = 2; }

message LoginRequest { string username = 1; string password = 2; }
message LoginResponse { string message = 1; int32 unread_count = 2; bool success = 3; }

message ListAccountsRequest { string username = 1; string pattern = 2; }
message ListAccountsResponse { repeated string accounts = 1; bool success = 2; }

message SendMessageRequest { string sender = 1; string to = 2; string content = 3; }
message SendMessageResponse { string message = 1; bool success = 2; }

message ReadNewMessagesRequest { string username = 1; int32 count = 2; }
message ReadNewMessagesResponse { repeated string messages = 1; bool success = 2; }

message DeleteMessagesRequest { string username = 1; repeated int32 message_ids = 2; }
message DeleteMessagesResponse { string message = 1; bool success = 2; }

message DeleteAccountRequest { string username = 1; }
message DeleteAccountResponse { string message = 1; bool success = 2; }

message ListMessagesRequest { string username = 1; }
message ListMessagesResponse { repeated string messages = 1; bool success = 2; }
```

*Note*: After editing the proto file, regenerate the gRPC modules using `grpcio-tools`.

---

## 7. Testing

### 7.1 Overview

We use **Python's `unittest`** framework for server-side testing. Tests ensure that each gRPC call (e.g., `CreateAccount`, `Login`, `SendMessage`) behaves correctly against an in-memory database (`users_db`). We also employ **coverage** to measure how much of the code our tests exercise.

### 7.2 Installing Test Dependencies

Make sure you have all necessary packages installed, including `coverage`:

```bash
pip install grpcio grpcio-tools protobuf coverage
```
- Use the following two commands to run the tests

```
python -m coverage run -m unittest discover -s .
python -m coverage report
```

 
---

## 8. Troubleshooting

1. **Connection Issues**
   - Ensure the server is running and that the host/port settings in `config.json` match on both client and server.
   - Check firewall settings or antivirus software that may block the gRPC port.

2. **Server Crashes**
   - Check the log file in the `logs/` directory (e.g. `chat_server_<timestamp>.log`) for exceptions or errors.

3. **Data Volatility**
   - Note that user accounts and messages are stored in memory. Restarting the server will erase all data (this is by design for demonstration purposes).

4. **Regex Filtering**
   - When listing accounts, ensure that your regex pattern is valid. Use simpler patterns if necessary.

---

## 9. Potential Improvements

- **Persistent Storage**
  - Integrate a database (e.g., SQLite, PostgreSQL) to store user accounts and messages persistently.

- **Enhanced Security**
  - Implement TLS/SSL for secure gRPC channels.
  - Use salted password hashes (e.g., with bcrypt) for stronger password protection.

- **Scalability**
  - Explore asynchronous frameworks or container orchestration if you expect high concurrency or large-scale deployment.

- **Additional Features**
  - Consider adding group chats, file attachments, real-time notifications, or user presence indicators.

---

## 10. License

This project is licensed under the MIT License.

---

**End of Documentation**
