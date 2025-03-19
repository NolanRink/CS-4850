import socket
import sys

# Constants
HOST = ''  # Bind to all interfaces (localhost and others)
PORT = 19953
USERFILE = 'users.txt'

# Load existing user credentials from file (if file not found, start with empty database)
users = {}
try:
    with open(USERFILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Expecting format: (UserID, Password)
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
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow quick reuse of the port
try:
    server_sock.bind((HOST, PORT))
except Exception as e:
    print(f"Failed to bind server on port {PORT}: {e}")
    sys.exit(1)
server_sock.listen(1)  # listen for one connection at a time

print("\nMy chat room server. Version One.\n")

# Accept and handle clients one by one
while True:
    conn, addr = server_sock.accept()
    # (Connection details are no longer printed.)
    logged_in_user = None  # no user logged in at start of connection
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                # Client disconnected (no data)
                break
            # Decode the received bytes to string and strip newline
            command_line = data.decode('utf-8', errors='ignore').strip()
            if not command_line:
                continue  # ignore empty lines

            # (Removed debug print for received commands)

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
                    response = f"Error: Already logged in as {logged_in_user}"
                else:
                    _, user_id, pwd = args
                    if user_id in users and users[user_id] == pwd:
                        logged_in_user = user_id
                        response = "login confirmed"
                        # Print server log for successful login (matches expected server output)
                        print(f"{logged_in_user} login.")
                    else:
                        response = "Denied. User name or password incorrect."

            elif command == "newuser":
                # Expected format: newuser <UserID> <Password>
                args = command_line.split()
                if len(args) != 3:
                    response = "Usage: newuser <UserID> <Password>"
                elif logged_in_user:
                    response = "Error: Cannot create new user while logged in"
                else:
                    _, new_user, new_pwd = args
                    # Enforce username and password length requirements
                    if len(new_user) < 3 or len(new_user) > 32:
                        response = "UserID must be 3-32 characters long"
                    elif len(new_pwd) < 4 or len(new_pwd) > 8:
                        response = "Password must be 4-8 characters long"
                    elif new_user in users:
                        response = "Denied. User account already exists."
                    else:
                        # Create the new user account
                        users[new_user] = new_pwd
                        try:
                            with open(USERFILE, 'a') as f:
                                f.write(f"\n({new_user}, {new_pwd})")
                            response = "New user account created."
                            # Print server log for new user creation
                            print("New user account created.")
                        except Exception as e:
                            users.pop(new_user, None)
                            response = "Error: Could not save new user."

            elif command == "send":
                # Expected format: send <message>
                if not logged_in_user:
                    response = "Denied. Please login first."
                else:
                    if len(parts) < 2 or parts[1] == "":
                        response = "Error: Message is empty"
                    else:
                        message = parts[1]
                        # Echo the message with the user's ID
                        response = f"{logged_in_user}: {message}"
                        # Print server log for sent message
                        print(response)

            elif command == "logout":
                # Expected format: logout
                if not logged_in_user:
                    response = "Error: You are not logged in"
                else:
                    response = f"{logged_in_user} left."
                    # Print server log for logout (matches expected server output)
                    print(f"{logged_in_user} logout.")
                    conn.sendall(response.encode('utf-8'))
                    break

            else:
                # Unknown command
                response = "Error: Unknown command"

            # Send back the response (if not already sent above)
            if response:
                try:
                    conn.sendall(response.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending response to client: {e}")
                    break
    finally:
        conn.close()
        # (Removed disconnection message.)
