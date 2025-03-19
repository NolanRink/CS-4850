import socket
import sys

# Default server address
SERVER_HOST = 'localhost'
SERVER_PORT = 19953

# Allow host and port override via command-line arguments (optional)
if len(sys.argv) >= 2:
    SERVER_HOST = sys.argv[1]
if len(sys.argv) >= 3:
    try:
        SERVER_PORT = int(sys.argv[2])
    except ValueError:
        print("Invalid port number. Using default 19953.")
        SERVER_PORT = 19953

# Connect to the server
client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_sock.connect((SERVER_HOST, SERVER_PORT))
except Exception as e:
    print(f"Could not connect to server {SERVER_HOST}:{SERVER_PORT} -> {e}")
    sys.exit(1)

print("\nMy chat room client. Version One.\n")

# Track login state on the client
logged_in = False
current_user = None

# Interactive command loop
try:
    while True:
        # Read a line of user input with a prompt that prints as expected
        try:
            user_input = input(">")
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

        # Enforce allowed commands based on login state:
        # - Logged out: only "login" and "newuser" are allowed.
        # - Logged in: only "send" and "logout" are allowed.
        if not logged_in:
            if cmd not in ("login", "newuser"):
                print("Denied. Please login first.")
                continue
        else:
            if cmd not in ("send", "logout"):
                print("Denied. Please login first.")
                continue

        # For login and newuser, enforce argument count and length restrictions.
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

        # Send the command to the server
        try:
            client_sock.sendall(command_line.encode('utf-8'))
        except Exception as e:
            print(">Connection to server lost.")
            break

        # Receive the server’s response
        try:
            data = client_sock.recv(1024)
        except Exception as e:
            print(">Connection to server lost.")
            break
        if not data:
            # No data means the server closed the connection
            print(">Server closed the connection.")
            break

        # Display the server's response (prefix with "> " for expected formatting)
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
    # Clean up the socket
    client_sock.close()
