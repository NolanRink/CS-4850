'''
Nolan Rink
CS 4850 Project V2
Due: 3/21/2025
Program Description: This is the client component of a chat room application.
'''

# Using Python version 3.12.0
import socket
import sys

# Default server address
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 19953

# Connect to the server
client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_sock.connect((SERVER_HOST, SERVER_PORT))
except Exception as e:
    print(f"Could not connect to server {SERVER_HOST}:{SERVER_PORT} -> {e}")
    sys.exit(1)

print("\nMy chat room client. Version One.\n")

# Track client login status and current user
logged_in = False
current_user = None

# Interactive command loop
try:
    while True:
        # Read a line of user input with a prompt that prints as expected
        try:
            user_input = input("> ")
        except EOFError:
            # Handle Ctrl+D / end-of-file as a signal to quit
            break
        if user_input is None:
            continue
        command_line = user_input.strip()
        if command_line == "":
            continue  # ignore empty input lines

        tokens = command_line.split()
        cmd = tokens[0].lower()

        # Logged out: only "login" and "newuser" are allowed.
        # Logged in: only "send" and "logout" are allowed.
        if not logged_in:
            if cmd not in ("login", "newuser"):
                if cmd in ("send", "logout"):
                    print("> Denied. Please login first.")
                else:
                    print("> Error: Unknown command")
                continue
        else:
            if cmd not in ("send", "logout"):
                print("> Denied. Please login first.")
                continue

        # For login and newuser, enforce argument count and length restrictions.
        if cmd in ("login", "newuser"):
            if len(tokens) != 3:
                print(f"> Usage: {cmd} <UserID> <Password>")
                continue
            _, user_id, pwd = tokens
            if len(user_id) < 3 or len(user_id) > 32:
                print("> UserID must be 3-32 characters long")
                continue
            if len(pwd) < 4 or len(pwd) > 8:
                print("> Password must be 4-8 characters long")
                continue

        if cmd == "send":
            message = command_line[4:].strip()  # Remove "send" and the following space
            if message == "":
                print("> Denied. Message is empty")
                continue
            if len(message) > 256 or len(message) < 1:
                print("> Denied. Message must be between 1 and 256 characters long")
                continue

        # Send the command to the server
        try:
            client_sock.sendall(command_line.encode('utf-8'))
        except Exception as e:
            print("> Connection to server lost.")
            break

        # Receive the server’s response
        try:
            data = client_sock.recv(1024)
        except Exception as e:
            print("> Connection to server lost.")
            break
        if not data:
            # No data means the server closed the connection
            print("> Server closed the connection.")
            break

        response = data.decode('utf-8', errors='ignore').strip()
        print("> " + response)

        # Update client-side state based on the command and response
        if cmd == "login":
            if response.lower() == "login confirmed":
                logged_in = True
                current_user = tokens[1]
            else:
                # Ensure state remains logged out if login failed.
                logged_in = False
        elif cmd == "logout":
            logged_in = False
            current_user = None
            break  # Exit the loop after logout

except KeyboardInterrupt:
    pass
finally:
    client_sock.close()
