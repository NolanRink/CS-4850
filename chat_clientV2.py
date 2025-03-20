# Using Python version 3.12.0
import socket
import sys
import threading

# Default server address and port
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 19953

if len(sys.argv) >= 2:
    SERVER_HOST = sys.argv[1]
if len(sys.argv) >= 3:
    try:
        SERVER_PORT = int(sys.argv[2])
    except ValueError:
        print("Invalid port number. Using default 19953.")
        SERVER_PORT = 19953

# Global client state
logged_in = False
current_user = None
running = True

# Connect to the server
client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_sock.connect((SERVER_HOST, SERVER_PORT))
except Exception as e:
    print(f"Could not connect to server {SERVER_HOST}:{SERVER_PORT} -> {e}")
    sys.exit(1)

print("\nMy chat room client. Version Two.\n")

def listen_for_messages(sock):
    global running, logged_in, current_user
    while running:
        try:
            data = sock.recv(1024)
            if not data:
                print(">Server closed the connection.")
                running = False
                break
            message = data.decode('utf-8', errors='ignore').strip()
            # Print received messages with the prompt prefix
            print("\n> " + message)
            # If the server confirms login, update state
            if message.lower() == "login confirmed":
                logged_in = True
            # If the received message indicates that our user has left, update state
            if current_user and message.lower() == f"{current_user.lower()} left.":
                logged_in = False
                current_user = None
        except Exception as e:
            print(">Connection to server lost.")
            running = False
            break

# Start a listener thread for asynchronous messages
listener_thread = threading.Thread(target=listen_for_messages, args=(client_sock,), daemon=True)
listener_thread.start()

try:
    while running:
        try:
            user_input = input(">")
        except EOFError:
            break
        if user_input is None:
            continue
        command_line = user_input.strip()
        if command_line == "":
            continue

        tokens = command_line.split()
        cmd = tokens[0].lower()

        # Enforce allowed commands:
        # - When logged out: only "login" and "newuser" are allowed.
        # - When logged in: only "send", "logout", and "who" are allowed.
        if not logged_in:
            if cmd not in ("login", "newuser"):
                if cmd in ("send", "logout", "who"):
                    print("Denied. Please login first.")
                else:
                    print("Error: Unknown command")
                continue
        else:
            if cmd not in ("send", "logout", "who"):
                print("Error: Unknown command.")
                continue

        # Enforce argument count and length restrictions for login and newuser
        if cmd in ("login", "newuser"):
            if len(tokens) != 3:
                print(f"Usage: {cmd} <UserID> <Password>")
                continue
            _, user_id, pwd = tokens
            if len(user_id) < 3 or len(user_id) > 32:
                print("UserID must be 3-32 characters long")
                continue
            if len(pwd) < 4 or len(pwd) > 8:
                print("Password must be 4-8 characters long")
                continue

        # For "send", enforce nonempty message and length restrictions.
        if cmd == "send":
            message_content = command_line[4:].strip()
            if message_content == "":
                print("Error: Message is empty")
                continue
            if len(message_content) < 1 or len(message_content) > 256:
                print("Error: Message must be between 1 and 256 characters long")
                continue

        # For login, store the current user (login confirmation comes from the server)
        if cmd == "login":
            current_user = tokens[1]

        try:
            client_sock.sendall(command_line.encode('utf-8'))
        except Exception as e:
            print(">Connection to server lost.")
            running = False
            break

        # If logout was issued, stop the loop.
        if cmd == "logout":
            running = False
            break

except KeyboardInterrupt:
    pass
finally:
    running = False
    client_sock.close()
