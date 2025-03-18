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

print(f"Connected to chat server at {SERVER_HOST}:{SERVER_PORT}")

# Interactive command loop
try:
    while True:
        # Read a line of user input
        try:
            user_input = input("> ")  # prompt for clarity
        except EOFError:
            # Handle Ctrl+D / end-of-file as a signal to quit
            break
        if user_input is None:
            continue
        command = user_input.strip()
        if command == "":
            continue  # ignore empty input lines

        # Send the command to the server
        try:
            client_sock.sendall(command.encode('utf-8'))
        except Exception as e:
            print("Connection to server lost.")
            break

        # Receive the server’s response
        try:
            data = client_sock.recv(1024)
        except Exception as e:
            print("Connection to server lost.")
            break
        if not data:
            # No data means the server closed the connection
            print("Server closed the connection.")
            break

        # Display the server's response
        response = data.decode('utf-8', errors='ignore').strip()
        print(response)

        # If the command was "logout", exit the loop after receiving the response
        if command.split()[0].lower() == "logout":
            break
finally:
    # Clean up the socket
    client_sock.close()
    print("Disconnected from chat server.")
