import socket
import argparse
import json
import os
import sys
import signal
import file_transfer as f_sys
from threading import Thread

client_socket = None        # To connect to the server
root_path ='./storage'      # Path to the storage folder

def signal_handler(sig, frame):
    global client_socket
    print('Terminating the Node...')

    request = "DISCONNECT"
    client_socket.sendall(request.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(f"EXIT response: {response}")

    client_socket.close()
    sys.exit(0)

def assign_global(cli_socket, root):
    global client_socket
    global root_path
    client_socket = cli_socket
    root_path = root

def get_default_interface():
    """
    Get the default IP address and an available port of the machine.
    Creates a dummy socket to determine these details without sending actual data.
    :return: A tuple (ip, port)
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("", 0))  # Bind to an ephemeral port
        s.connect(("8.8.8.8", 80))  # Simulate a connection to get the IP
        ip = s.getsockname()[0]
        port = s.getsockname()[1]
    except Exception:
        ip, port = "127.0.0.1", 100
    finally:
        s.close()
    return ip, port

def connect_to_tracker(server_ip, server_port, node_ip, node_port):
    """
    :return: The connected socket object or None if the connection fails.
    """
    global client_socket
    try:
        # Create and connect the socket to the server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, server_port))
        print(f"Connected to server at {server_ip}:{server_port}")

        # Register the node and its files immediately after connection
        register_node(node_ip, node_port)

        register_files()
        return client_socket

    except socket.error as e:
        print(f"Error connecting to server: {e}")
        return None

def register_node(ip, port):
    global client_socket
    try:
        message = f"REGISTER_NODE {ip} {port}"
        client_socket.sendall(message.encode())
        print(f"Sent registration message: {message}")

        respone = client_socket.recv(1024).decode("utf-8")
        print(f"Server response: {respone}")
    except socket.error as e:
        print(f"Error sending registration message: {e}")

def register_files():
    global client_socket
    global root_path
    if not os.path.exists(root_path):
        print(f"Storage path {root_path} does not exist.")
        return

    for file_name in os.listdir(root_path):
        file_path = os.path.join(root_path, file_name)
        if os.path.isfile(file_path):
            try:
                pieces_metadata = f_sys.split_file(file_path)  # Split the file and get metadata
                magnet_link = f_sys.generate_magnet_link(os.path.basename(file_path), pieces_metadata)
                total_piece = len(pieces_metadata)
                command = f"REGISTER_FILE {file_name} {total_piece} {magnet_link}"

                client_socket.sendall(command.encode('utf-8'))
                print(f"Registered file: {file_name} with magnet link: {magnet_link}")

                respone = client_socket.recv(1024).decode('utf-8')
                print(f"Server response: {respone}")
                
            except Exception as e:
                print(f"Error registering file {file_name}: {e}")

def send_runtime_commands():
    print("You can now enter runtime commands. Type 'exit' to quit.")
    global client_socket
    try:
        while True:
            command = input("Node CLI >")
            if command.lower() == "exit":
                print("Closing connection...")
                client_socket.sendall("DISCONNECT".encode())
                break

            elif command.startswith("REGISTTER_FILE"):
                '''
                REGISTTER_FILE <file_name> <total_piece> <magnet_link>
                '''
                try:
                    file_path = command.split(" ", 1)[1]  # Extract file path from command
                    pieces_metadata = f_sys.split_file(file_path)  # Split the file and get metadata

                    magnet_link = f_sys.generate_magnet_link(os.path.basename(file_path), pieces_metadata)
                    request = f"{command} {magnet_link}"  
                    client_socket.sendall(request.encode())  
                    print(f"Sent request: {request}")
                except Exception as e:
                    print(f"Error processing REGISTER_FILE command: {e}")

            #Use for manual input files
            elif command.startswith("FIND_FILE"):
                client_socket.sendall(command.encode())  #  FIND_FILE <file_name>
                
                # Receive and parse server response
                response = client_socket.recv(1024 * 20).decode('utf-8')

                f_sys.parse_find_file_response(response)

            elif command.startswith("PING"):
                try:
                    _, target_ip, target_port = command.split()
                    target_port = int(target_port)
                    
                    # Create a new socket for the ping
                    ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    ping_socket.settimeout(5)  # Set a timeout for the connection attempt

                    print(f"Pinging {target_ip}:{target_port}...")
                    ping_socket.connect((target_ip, target_port))
                    ping_socket.sendall("PING".encode('utf-8'))

                    # Wait for a response
                    response = ping_socket.recv(1024).decode()
                    if response == "PONG":
                        print(f"Ping to {target_ip}:{target_port} successful.")
                    else:
                        print(f"Unexpected response from {target_ip}:{target_port}: {response}")

                    ping_socket.close()
                except Exception as e:
                    print(f"Error processing PING command: {e}")

            # Wait for server response
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")

            # Wait for server response
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")
    except Exception as e:
        print(f"Error in runtime commands: {e}")
    finally:
        client_socket.close()

def listen_for_messages():
    global client_socket
    try:
        while True:
            data = client_socket.recv(1024).decode("utf-8").strip()
            if not data:
                print("Connection closed by server.")
                break
            print(f"Received from server: {data}")
            
            if data == "PING":
                client_socket.sendall("PONG".encode())

                
    except Exception as e:
        print(f"Error in listening for messages: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to a pre-declared server and register as a node.",
        epilog="!!!Ensure the server is running and listening before starting!!!",
    )
    parser.add_argument("--server-ip", required=True, help="IP address of the server.")
    parser.add_argument("--server-port", type=int, required=True, help="Port of the server.")
    parser.add_argument("--root-folder", required=True, help="Root folder.")

    args = parser.parse_args()

    # Extract arguments
    server_ip = args.server_ip
    server_port = args.server_port

    client_ip, client_port = get_default_interface()  # Automatically detect the node's IP

    print(f"Node IP detected: {client_ip}")
    print(f"Node Port specified: {client_port}")

    # Establish client process
    client_socket = connect_to_tracker(server_ip, server_port, client_ip, client_port)
    if client_socket:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        assign_global(client_socket, args.root_folder)
        
        # Start the listening thread
        listening_thread = Thread(target=listen_for_messages, daemon=True)
        listening_thread.start()

        # Start the CLI thread
        cli_thread = Thread(target=send_runtime_commands)
        cli_thread.start()

        # Wait for the CLI thread to finish
        cli_thread.join()

        client_socket.close()  # Close the connection when done
        print("Connection closed.")