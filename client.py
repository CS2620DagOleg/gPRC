import os
import json
import tkinter as tk
from tkinter import messagebox, simpledialog
import grpc
import hashlib

import chat_pb2
import chat_pb2_grpc

# ---------------------------
# Load configuration
# ---------------------------
with open("config.json", "r") as config_file:
    config = json.load(config_file)

SERVER_HOST = config.get("client_connect_host", "localhost")
SERVER_PORT = config.get("server_port", 50051)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class ChatClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chat Client")
        self.geometry("400x350")
        self.current_user = None

        # Create a gRPC channel and stub to communicate with the server.
        channel_address = f"{SERVER_HOST}:{SERVER_PORT}"
        self.channel = grpc.insecure_channel(channel_address)
        self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        self.frames = {}
        for FrameClass in (StartFrame, MainFrame):
            frame = FrameClass(parent=container, controller=self)
            self.frames[FrameClass] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame(StartFrame)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()

    def set_current_user(self, username):
        self.current_user = username

    def get_current_user(self):
        return self.current_user

    def cleanup(self):
        # For gRPC, simply closing the Tkinter window is enough.
        self.destroy()

class StartFrame(tk.Frame):
    def __init__(self, parent, controller: ChatClientApp):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Welcome to the Chat Client", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Button(self, text="Create Account", width=20, command=self.create_account).pack(pady=5)
        tk.Button(self, text="Login", width=20, command=self.login).pack(pady=5)
        tk.Button(self, text="Exit", width=20, command=self.exit_app).pack(pady=5)

    def create_account(self):
        username = simpledialog.askstring("Create Account", "Enter a new username:", parent=self)
        if not username:
            return
        password = simpledialog.askstring("Create Account", "Enter a new password:", parent=self, show="*")
        if not password:
            return

        hashed_pass = hash_password(password)
        request = chat_pb2.CreateAccountRequest(username=username, password=hashed_pass)
        try:
            response = self.controller.stub.CreateAccount(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messagebox.showinfo("Success", response.message)
        else:
            messagebox.showerror("Error", response.message)

    def login(self):
        username = simpledialog.askstring("Login", "Enter username:", parent=self)
        if not username:
            return
        password = simpledialog.askstring("Login", "Enter password:", parent=self, show="*")
        if not password:
            return

        hashed_pass = hash_password(password)
        request = chat_pb2.LoginRequest(username=username, password=hashed_pass)
        try:
            response = self.controller.stub.Login(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            self.controller.set_current_user(username)
            messagebox.showinfo("Logged In", f"{response.message}\nUnread messages: {response.unread_count}")
            self.controller.show_frame(MainFrame)
        else:
            messagebox.showerror("Error", response.message)

    def exit_app(self):
        self.controller.cleanup()

class MainFrame(tk.Frame):
    def __init__(self, parent, controller: ChatClientApp):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Main Menu", font=("Arial", 14, "bold")).pack(pady=10)
        self.logged_in_label = tk.Label(self, text="", font=("Arial", 10, "italic"))
        self.logged_in_label.pack(pady=(0, 10))

        tk.Button(self, text="List Accounts", width=20, command=self.list_accounts).pack(pady=5)
        tk.Button(self, text="Send Message", width=20, command=self.send_message).pack(pady=5)
        tk.Button(self, text="Read New Messages", width=20, command=self.read_new_messages).pack(pady=5)
        tk.Button(self, text="Show All Messages", width=20, command=self.show_all_messages).pack(pady=5)
        tk.Button(self, text="Delete My Account", width=20, command=self.delete_account).pack(pady=5)
        tk.Button(self, text="Logout", width=20, command=self.logout).pack(pady=5)

    def tkraise(self, aboveThis=None):
        user = self.controller.get_current_user()
        if user:
            self.logged_in_label.config(text=f"Logged in as: {user}")
        else:
            self.logged_in_label.config(text="Not logged in")
        super().tkraise(aboveThis)

    def list_accounts(self):
        pattern = simpledialog.askstring("List Accounts", "Enter wildcard pattern (or leave blank):", parent=self)
        if pattern is None:
            pattern = ""
        request = chat_pb2.ListAccountsRequest(username=self.controller.get_current_user(), pattern=pattern)
        try:
            response = self.controller.stub.ListAccounts(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            accounts = response.accounts
            msg = "\n".join(accounts) if accounts else "No matching accounts found."
            messagebox.showinfo("Accounts", msg)
        else:
            messagebox.showerror("Error", "Error listing accounts.")

    def send_message(self):
        recipient = simpledialog.askstring("Send Message", "Recipient username:", parent=self)
        if not recipient:
            return
        content = simpledialog.askstring("Send Message", "Message content:", parent=self)
        if content is None:
            return
        request = chat_pb2.SendMessageRequest(
            sender=self.controller.get_current_user(),
            to=recipient,
            content=content
        )
        try:
            response = self.controller.stub.SendMessage(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messagebox.showinfo("Success", response.message)
        else:
            messagebox.showerror("Error", response.message)

    def read_new_messages(self):
        count_str = simpledialog.askstring("Read New Messages", "How many new messages to read? (leave blank for all)", parent=self)
        if count_str is None or count_str.strip() == "":
            count = 0
        else:
            try:
                count = int(count_str)
            except ValueError:
                count = 0
        request = chat_pb2.ReadNewMessagesRequest(username=self.controller.get_current_user(), count=count)
        try:
            response = self.controller.stub.ReadNewMessages(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messages = response.messages
            if messages:
                display_str = "\n".join(f"{idx+1}. {msg}" for idx, msg in enumerate(messages))
                messagebox.showinfo("New Messages", display_str)
            else:
                messagebox.showinfo("New Messages", "No new messages.")
        else:
            messagebox.showerror("Error", "Error reading messages.")

    def show_all_messages(self):
        request = chat_pb2.ListMessagesRequest(username=self.controller.get_current_user())
        try:
            response = self.controller.stub.ListMessages(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messages = response.messages
            ShowMessagesWindow(self.controller, messages)
        else:
            messagebox.showerror("Error", "Error listing messages.")

    def delete_account(self):
        confirm = messagebox.askyesno("Delete Account", "Are you sure you want to delete this account?\nUnread messages will be lost.")
        if not confirm:
            return
        request = chat_pb2.DeleteAccountRequest(username=self.controller.get_current_user())
        try:
            response = self.controller.stub.DeleteAccount(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messagebox.showinfo("Account Deleted", response.message)
            self.controller.set_current_user("")
            self.controller.show_frame(StartFrame)
        else:
            messagebox.showerror("Error", response.message)

    def logout(self):
        self.controller.set_current_user("")
        self.controller.show_frame(StartFrame)

class ShowMessagesWindow(tk.Toplevel):
    def __init__(self, controller: ChatClientApp, messages):
        super().__init__()
        self.controller = controller
        self.title("All Messages")
        self.geometry("400x300")
        tk.Label(self, text="All Read Messages", font=("Arial", 12, "bold")).pack(pady=5)
        self.messages = messages
        self.check_vars = []
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        for idx, msg in enumerate(self.messages, start=1):
            var = tk.BooleanVar()
            chk = tk.Checkbutton(
                self.frame,
                text=f"{idx}. {msg}",
                variable=var,
                anchor="w",
                justify="left",
                wraplength=350
            )
            chk.pack(fill="x", padx=5, pady=2)
            self.check_vars.append((var, idx))
        tk.Button(self, text="Delete Selected", command=self.delete_selected).pack(pady=5)
        tk.Button(self, text="Close", command=self.destroy).pack(pady=5)

    def delete_selected(self):
        selected = [idx for var, idx in self.check_vars if var.get()]
        if not selected:
            messagebox.showinfo("Info", "No messages selected.")
            return
        request = chat_pb2.DeleteMessagesRequest(username=self.controller.get_current_user(), message_ids=selected)
        try:
            response = self.controller.stub.DeleteMessages(request)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if response.success:
            messagebox.showinfo("Success", response.message)
            self.destroy()
        else:
            messagebox.showerror("Error", response.message)

def main():
    app = ChatClientApp()
    app.protocol("WM_DELETE_WINDOW", app.cleanup)
    app.mainloop()

if __name__ == "__main__":
    main()
