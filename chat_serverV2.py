# Using Python version 3.12.0
import socket
import sys
import threading
import os

MAXCLIENTS = 3

HOST = '127.0.0.1'
PORT = 19953
USERFILE = 'users.txt'

# Dictionary mapping username -> connection socket
active_clients = {}
active_clients_lock = threading.Lock()
# List to maintain the login order for the "who" command
online_order = []
online_order_lock = threading.Lock()

# Load existing users from file formatted as: (UserID, Password)
users = {}
try:
    with open(USERFILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("(") and line.endswith(")"):
                line = line[1:-1]
            parts = line.split(',')
            if len(parts) >= 2:
                username = parts[0].strip()
                password = parts[1].strip()
                users[username] = password
except FileNotFoundError:
    users = {}

def broadcast_message(message, exclude_conn=None):
    with active_clients_lock:
        for user, client_conn in active_clients.items():
            if client_conn != exclude_conn:
                try:
                    client_conn.sendall(message.encode('utf-8'))
                except Exception:
                    pass

def handle_client(conn, addr):
    global active_clients, online_order
    logged_in_user = None
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            command_line = data.decode('utf-8', errors='ignore').strip()
            if not command_line:
                continue

            tokens = command_line.split()
            cmd = tokens[0].lower()
            response = ""

            if cmd == "login":
                if len(tokens) != 3:
                    response = "Usage: login <UserID> <Password>"
                elif logged_in_user:
                    response = f"Error: Already logged in as {logged_in_user}"
                else:
                    user_id = tokens[1]
                    pwd = tokens[2]
                    if user_id in users and users[user_id] == pwd:
                        logged_in_user = user_id
                        with active_clients_lock:
                            active_clients[logged_in_user] = conn
                        with online_order_lock:
                            online_order.append(logged_in_user)
                        response = "login confirmed"
                        print(f"{logged_in_user} login.")
                        # Notify others that this user has joined
                        broadcast_message(f"{logged_in_user} joins.", exclude_conn=conn)
                    else:
                        response = "Denied. User name or password incorrect."

            elif cmd == "newuser":
                if len(tokens) != 3:
                    response = "Usage: newuser <UserID> <Password>"
                elif logged_in_user:
                    response = "Error: Cannot create new user while logged in"
                else:
                    new_user = tokens[1]
                    new_pwd = tokens[2]
                    if len(new_user) < 3 or len(new_user) > 32:
                        response = "UserID must be 3-32 characters long"
                    elif len(new_pwd) < 4 or len(new_pwd) > 8:
                        response = "Password must be 4-8 characters long"
                    elif new_user in users:
                        response = "Denied. User account already exists."
                    else:
                        users[new_user] = new_pwd
                        try:
                            if os.path.exists(USERFILE):
                                with open(USERFILE, 'rb+') as f:
                                    f.seek(0, os.SEEK_END)
                                    if f.tell() > 0:
                                        f.seek(-1, os.SEEK_END)
                                        if f.read(1) != b'\n':
                                            f.write(b'\n')
                            with open(USERFILE, 'a') as f:
                                f.write(f"({new_user}, {new_pwd})\n")
                            response = "New user account created."
                            print("New user account created.")
                        except Exception as e:
                            users.pop(new_user, None)
                            response = "Error: Could not save new user."

            elif cmd == "send":
                if not logged_in_user:
                    response = "Denied. Please login first."
                else:
                    # Split into at most 3 parts: command, target, and message
                    parts = command_line.split(' ', 2)
                    if len(parts) < 2:
                        response = "Usage: send <target> <message>"
                    else:
                        target = parts[1]
                        if target.lower() == "all":
                            if len(parts) < 3 or parts[2].strip() == "":
                                response = "Error: Message is empty"
                            elif len(parts[2]) > 256:
                                response = "Error: Message must be between 1 and 256 characters long"
                            else:
                                message = parts[2]
                                full_message = f"{logged_in_user}: {message}"
                                # Broadcast to everyone except the sender
                                broadcast_message(full_message, exclude_conn=conn)
                                print(full_message)
                                response = ""
                        else:
                            if len(parts) < 3 or parts[2].strip() == "":
                                response = "Error: Message is empty"
                            elif len(parts[2]) > 256:
                                response = "Error: Message must be between 1 and 256 characters long"
                            else:
                                message = parts[2]
                                full_message = f"{logged_in_user}: {message}"
                                with active_clients_lock:
                                    target_conn = active_clients.get(target)
                                if target_conn:
                                    try:
                                        target_conn.sendall(full_message.encode('utf-8'))
                                        print(f"{logged_in_user} (to {target}): {message}")
                                        response = ""
                                    except Exception as e:
                                        response = f"Error: Could not send message to {target}."
                                else:
                                    response = f"Error: User {target} is not online."

            elif cmd == "who":
                if not logged_in_user:
                    response = "Denied. Please login first."
                else:
                    with online_order_lock:
                        response = ", ".join(online_order)

            elif cmd == "logout":
                if not logged_in_user:
                    response = "Error: You are not logged in"
                else:
                    response = f"{logged_in_user} left."
                    print(f"{logged_in_user} logout.")
                    broadcast_message(response, exclude_conn=conn)
                    with active_clients_lock:
                        if logged_in_user in active_clients:
                            del active_clients[logged_in_user]
                    with online_order_lock:
                        if logged_in_user in online_order:
                            online_order.remove(logged_in_user)
                    conn.sendall(response.encode('utf-8'))
                    break

            else:
                response = "Error: Unknown command"

            if response:
                try:
                    conn.sendall(response.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending response to client: {e}")
                    break
    except Exception as e:
        pass
    finally:
        conn.close()
        if logged_in_user:
            with active_clients_lock:
                if logged_in_user in active_clients:
                    del active_clients[logged_in_user]
            with online_order_lock:
                if logged_in_user in online_order:
                    online_order.remove(logged_in_user)

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind((HOST, PORT))
    except Exception as e:
        print(f"Failed to bind server on port {PORT}: {e}")
        sys.exit(1)
    server_sock.listen(MAXCLIENTS)
    print("\nMy chat room server. Version Two.\n")
    try:
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        pass
    server_sock.close()

if __name__ == "__main__":
    main()
