# Using Python version 3.12.0
import socket
import sys

HOST = '127.0.0.1' 
PORT = 19953
USERFILE = 'users.txt'

# Load existing user credentials from file 
users = {}
try:
    with open(USERFILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("(") and line.endswith(")"):
                line = line[1:-1]  # Remove the surrounding parentheses
            parts = line.split(',')
            if len(parts) >= 2:
                username = parts[0].strip()
                password = parts[1].strip()
                users[username] = password
except FileNotFoundError:
    users = {}

# Create a TCP socket and bind it to the port
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    server_sock.bind((HOST, PORT))
except Exception as e:
    print(f"Failed to bind server on port {PORT}: {e}")
    sys.exit(1)
server_sock.listen(1)  # listen for one connection at a time

print("\nMy chat room server. Version One.\n")

try:
    # Accept and handle clients one by one
    while True:
        conn, addr = server_sock.accept()
        logged_in_user = None  
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    # Client disconnected
                    break
                # Decode the received bytes to string and strip newline
                command_line = data.decode('utf-8', errors='ignore').strip()
                if not command_line:
                    continue  # ignore empty lines

                # Split the input into command and argument(s)
                parts = command_line.split(' ', 1)
                command = parts[0].lower()  # command word in lowercase
                response = ""

                if command == "login":
                    # Expected format: login <UserID> <Password>
                    args = command_line.split()
                    if len(args) != 3:
                        response = "Usage: login <UserID> <Password>"
                    elif logged_in_user:
                        response = f"Denied. Already logged in as {logged_in_user}"
                    else:
                        _, user_id, pwd = args
                        if user_id in users and users[user_id] == pwd:
                            logged_in_user = user_id
                            response = "login confirmed"
                            print(f"{logged_in_user} login.")
                        else:
                            response = "Denied. User name or password incorrect."

                elif command == "newuser":
                    # Expected format: newuser <UserID> <Password>
                    args = command_line.split()
                    if len(args) != 3:
                        response = "Usage: newuser <UserID> <Password>"
                    elif logged_in_user:
                        response = "Denied. Cannot create new user while logged in"
                    else:
                        _, new_user, new_pwd = args
                        # Enforce username and password length requirements
                        if new_user in users:
                            response = "Denied. User account already exists."
                        else:
                            # Create the new user account
                            users[new_user] = new_pwd
                            try:
                                with open(USERFILE, 'a') as f:
                                    f.write(f"\n({new_user}, {new_pwd})")
                                response = "New user account created. Please login."
                                # Print server log for new user creation
                                print("New user account created.")
                            except Exception as e:
                                users.pop(new_user, None)
                                response = "Denied. Could not save new user."

                elif command == "send":
                    # Expected format: send <message>
                    if not logged_in_user:
                        response = "Denied. Please login first."
                    else:
                        if len(parts) < 2 or parts[1] == "":
                            response = "Denied. Message is empty"
                        else:
                            message = parts[1]
                            response = f"{logged_in_user}: {message}"
                            print(response)

                elif command == "logout":
                    # Expected format: logout
                    if not logged_in_user:
                        response = "Denied. You are not logged in"
                    else:
                        response = f"{logged_in_user} left."
                        print(f"{logged_in_user} logout.")
                        conn.sendall(response.encode('utf-8'))
                        break
                else:
                    # Unknown command
                    response = "Denied. Unknown command"

                # Send back the response (if not already sent above)
                if response:
                    try:
                        conn.sendall(response.encode('utf-8'))
                    except Exception as e:
                        print(f"Error sending response to client: {e}")
                        break
        finally:
            conn.close()
except KeyboardInterrupt:
    print("\nKeyboard interrupt received. Shutting down the server.")
finally:
    server_sock.close()
    sys.exit(0)