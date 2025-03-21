'''
Nolan Rink
CS 4850 Project V2
Due: 3/21/2025
Program Description: This is the server component of a chat room application.
'''

# Using Python version 3.12.0

import socket      
import sys         
import threading   
import os          

# Maximum number of concurrent clients allowed
MAXCLIENTS = 3

# Server network configuration
HOST = '127.0.0.1'    # Localhost IP address
PORT = 19953          
USERFILE = 'users.txt'  

# Dictionary mapping username -> connection socket for active clients
active_clients = {}
active_clients_lock = threading.Lock()  

# List to maintain the login order for the "who" command
online_order = []
online_order_lock = threading.Lock()  

# Load existing users from the file formatted as: (UserID, Password)
users = {}
try:
    with open(USERFILE, 'r') as f:
        for line in f:
            line = line.strip()  # Remove leading/trailing whitespace
            if not line:
                continue  # Skip empty lines
            if line.startswith("(") and line.endswith(")"):
                line = line[1:-1]  # Remove surrounding parentheses if present
            parts = line.split(',')  # Split into username and password parts
            if len(parts) >= 2:
                username = parts[0].strip()
                password = parts[1].strip()
                users[username] = password  
except FileNotFoundError:
    users = {}

def broadcast_message(message, exclude_conn=None):
    """
    Broadcasts a message to all connected clients except the one specified by exclude_conn.
    This function iterates over all active clients and sends the encoded message.
    """
    with active_clients_lock:
        for user, client_conn in active_clients.items():
            if client_conn != exclude_conn:
                try:
                    client_conn.sendall(message.encode('utf-8'))
                except Exception:
                    pass

def handle_client(conn, addr):
    """
    Handles an individual client connection.
    Processes commands from the client, updates server state, and responds accordingly.
    """
    global active_clients, online_order
    logged_in_user = None  

    try:
        while True:
            data = conn.recv(1024)  
            if not data:
                break  # If no data, client has disconnected; exit loop
            command_line = data.decode('utf-8', errors='ignore').strip()
            if not command_line:
                continue  # Ignore empty commands

            tokens = command_line.split()  
            cmd = tokens[0].lower()  
            response = ""  

            # Command: login <UserID> <Password>
            if cmd == "login":
                if len(tokens) != 3:
                    response = "Usage: login <UserID> <Password>"
                elif logged_in_user:
                    response = f"Error: Already logged in as {logged_in_user}"
                else:
                    user_id = tokens[1]
                    pwd = tokens[2]
                    if user_id in users and users[user_id] == pwd:
                        logged_in_user = user_id  # Mark client as logged in
                        with active_clients_lock:
                            active_clients[logged_in_user] = conn  # Add to active clients
                        with online_order_lock:
                            online_order.append(logged_in_user)  # Record login order
                        response = "login confirmed"
                        print(f"{logged_in_user} login.")
                        # Notify all other clients that a new user has joined
                        broadcast_message(f"{logged_in_user} joins.", exclude_conn=conn)
                    else:
                        response = "Denied. User name or password incorrect."

            # Command: newuser <UserID> <Password>
            elif cmd == "newuser":
                if len(tokens) != 3:
                    response = "Usage: newuser <UserID> <Password>"
                elif logged_in_user:
                    response = "Error: Cannot create new user while logged in"
                else:
                    new_user = tokens[1]
                    new_pwd = tokens[2]
                    # Enforce length restrictions: UserID must be 3-32 chars, Password 4-8 chars
                    if len(new_user) < 3 or len(new_user) > 32:
                        response = "UserID must be 3-32 characters long"
                    elif len(new_pwd) < 4 or len(new_pwd) > 8:
                        response = "Password must be 4-8 characters long"
                    elif new_user in users:
                        response = "Denied. User account already exists."
                    else:
                        users[new_user] = new_pwd  # Add new user to the dictionary
                        try:
                            # Ensure the file has proper newline formatting before appending
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
                            # If file writing fails, remove the new user from the dictionary
                            users.pop(new_user, None)
                            response = "Error: Could not save new user."

            # Command: send <target> <message>
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
                        # Check if message is for broadcasting to all clients
                        if target.lower() == "all":
                            if len(parts) < 3 or parts[2].strip() == "":
                                response = "Error: Message is empty"
                            elif len(parts[2]) > 256:
                                response = "Error: Message must be between 1 and 256 characters long"
                            else:
                                message = parts[2]
                                full_message = f"{logged_in_user}: {message}"
                                # Broadcast the message to all clients except the sender
                                broadcast_message(full_message, exclude_conn=conn)
                                print(full_message)
                                response = ""
                        # Unicast: send message to a specific user
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

            # Command: who
            elif cmd == "who":
                if not logged_in_user:
                    response = "Denied. Please login first."
                else:
                    with online_order_lock:
                        response = ", ".join(online_order)

            # Command: logout
            elif cmd == "logout":
                if not logged_in_user:
                    response = "Error: You are not logged in"
                else:
                    response = f"{logged_in_user} left."
                    print(f"{logged_in_user} logout.")
                    # Broadcast to all clients that the user has left
                    broadcast_message(response, exclude_conn=conn)
                    with active_clients_lock:
                        if logged_in_user in active_clients:
                            del active_clients[logged_in_user]
                    with online_order_lock:
                        if logged_in_user in online_order:
                            online_order.remove(logged_in_user)
                    # Send the logout confirmation to the client before breaking the loop
                    conn.sendall(response.encode('utf-8'))
                    break

            # If the command is not recognized, send an error message
            else:
                response = "Error: Unknown command"

            # Send the response to the client, if there is any response to send
            if response:
                try:
                    conn.sendall(response.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending response to client: {e}")
                    break

    except Exception as e:
        # Catch all exceptions to prevent server crash due to a single client error
        pass
    finally:
        # Clean up: close the connection and remove the user from active lists if necessary
        conn.close()
        if logged_in_user:
            with active_clients_lock:
                if logged_in_user in active_clients:
                    del active_clients[logged_in_user]
            with online_order_lock:
                if logged_in_user in online_order:
                    online_order.remove(logged_in_user)

def main():
    """
    Main function to start the chat server.
    It creates a socket, binds to the specified host and port,
    listens for incoming client connections, and spawns a new thread for each client.
    """
    # Create a TCP/IP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Set socket options to allow reusing the address (prevents "address already in use" errors)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        # Bind the socket to the configured host and port
        server_sock.bind((HOST, PORT))
    except Exception as e:
        print(f"Failed to bind server on port {PORT}: {e}")
        sys.exit(1)
    # Start listening for incoming connections with a limit of MAXCLIENTS in the queue
    server_sock.listen(MAXCLIENTS)
    print("\nMy chat room server. Version Two.\n")
    try:
        while True:
            # Accept a new client connection
            conn, addr = server_sock.accept()
            # Start a new thread to handle the client connection
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        # Allow graceful shutdown on Ctrl+C
        pass
    server_sock.close()  # Close the server socket when done

# Entry point of the program
if __name__ == "__main__":
    main()
