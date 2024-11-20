import socket
import argparse
import json
import os
import sys
import signal
import file_transfer as f_sys
from threading import Thread, Event

root_path = './storage'
tracker_ip = None
tracker_port = None
this_ip = None
this_port = None

stop_server = Event()

#GETTERS
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
        port = 10000  # Default port
    except Exception:
        ip, port = "192.168.56.104", 10000
    finally:
        s.close()
    return ip, port

def get_ephemeral_port():
    """
    Establish a connection to the tracker using an ephemeral port.
    :return: A connected socket object.
    """
    global tracker_ip, tracker_port

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(("", 0))  # Bind to an ephemeral port
    client_socket.connect((tracker_ip, tracker_port))
    client_socket.settimeout(5)
    return client_socket

#INITIALIZERS
def assign_global(server_ip, server_port, root_folder, node_ip, node_port):
    global tracker_ip, tracker_port, root_path, this_ip, this_port
    root_path = root_folder
    tracker_ip = server_ip
    tracker_port = server_port
    this_ip = node_ip
    this_port = node_port

def register_node(ephemeral_socket):
    global this_ip, this_port

    try:
        request = f"REGISTER_NODE {this_ip} {this_port}"
        ephemeral_socket.sendall(request.encode('utf-8'))
        print(f"Sent registration message: {request}")

        respone = ephemeral_socket.recv(1024).decode("utf-8")
        print(f"Server response: {respone}")

    except socket.error as e:
        print(f"Error sending registration message: {e}")

def register_files(ephemeral_socket):
    global root_path, this_ip, this_port

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

                request = f"REGISTER_FILE {this_ip} {this_port} {file_name} {total_piece} {magnet_link}"

                ephemeral_socket.sendall(request.encode('utf-8'))
                print(f"Registered file: {file_name} with magnet link: {magnet_link}")

                respone = ephemeral_socket.recv(1024).decode('utf-8')
                print(f"Server response: {respone}")
                
            except Exception as e:
                print(f"Error registering file {file_name}: {e}")

def connect_to_tracker():
    ephemeral_socket = get_ephemeral_port()

    try:        
        register_node(ephemeral_socket)
        register_files(ephemeral_socket)

    except Exception as e:
        print(f"Error connecting to tracker: {e}")

    finally:
        if ephemeral_socket:
            ephemeral_socket.close()

# Thread-related functions
def start_server_process(ip, port):
    """
    Start a server process that continuously listens for incoming connections.
    :param ip: IP address to bind the server to.
    :param port: Port to bind the server to.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip, port))
    server_socket.listen(5)

    print(f"Node listening on {ip}:{port}")
    global stop_server

    try:
        while not stop_server.is_set():
            client_socket, client_addr = server_socket.accept()
            print(f"Accepted connection from {client_addr}")

            # Handle the client connection in a separate thread
            client_thread = Thread(target=handle_income_request, args=(client_socket,))
            client_thread.start()
            client_thread.join()
    except Exception as e:
        print(f"Error in server process: {e}")
    finally:
        server_socket.close()

def handle_income_request(client_conn):
    """
    Handle the communication with a connected client.
    :param client_conn: The socket object for the client connection.
    """
    global stop_server
    try:
        while not stop_server.is_set():
            data = client_conn.recv(1024).decode("utf-8").strip()
            if not data:
                print("Client disconnected.")
                break
            print(f"Received from client: {data}")

            # Echo the received data back to the client
            client_conn.sendall(data.encode("utf-8"))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_conn.close()
    
def handle_cli_input(this_ip, this_port):
    # Bind to an ephemeral port
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(("", 0))  # Bind to an ephemeral port
    client_socket.connect((tracker_ip, tracker_port))
    print(f"Connected to tracker at {tracker_ip}:{tracker_port}")

    print("You can now enter runtime commands. Type 'exit' to quit.")
    try:
        while True:
            command = input("Node CLI >")

            if command.lower() == "exit":
                stop_server.set()
                print("Closing connection...")
                break

            #Use for manual input files
            # elif command.startswith("REGISTTER_FILE"):
            #     '''
            #     input: REGISTER_FILE <file_name>
            #     Send Request: REGISTTER_FILE <this_ip> <this_port> <file_name> <total_piece> <magnet_link>
            #     '''
            #     try:
            #         _, file_path = command.split() # Extract file path from command
            #         pieces_metadata = f_sys.split_file(file_path)  # Split the file and get metadata

            #         magnet_link = f_sys.generate_magnet_link(os.path.basename(file_path), pieces_metadata)

            #         request = f"{command} {magnet_link}"  
            #         client_socket.sendall(request.encode())  
            #         print(f"Sent request: {request}")
            #     except Exception as e:
            #         print(f"Error processing REGISTER_FILE command: {e}")

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

#Cleaning up functions
def cleaning_up(sig, frame):
    global stop_server
    stop_server.set()
    print("Interrupt received, shutting down...")

    ephemeral_socket = get_ephemeral_port()
    # Send disconnect message to the tracker
    try:
        REQUEST = f"DISCONNECT_NODE {this_ip} {this_port}"
        ephemeral_socket.sendall(REQUEST.encode('utf-8'))
        print(f"Sent disconnect message: {REQUEST}")

        RESPONSE = ephemeral_socket.recv(1024).decode('utf-8')
        print(f"Server response: {RESPONSE}")

        sys.exit(0)

    except Exception as e:
        print(f"Error sending disconnect message: {e}")

    finally:
        ephemeral_socket.close()

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
    tracker_ip = args.server_ip
    tracker_port = args.server_port

    #personal IP and port (this_ip, this_port)
    pserver_ip, pserver_port = get_default_interface()  # Automatically detect the node's IP

    print(f"Node IP detected: {pserver_ip}")
    print(f"Node Port specified: {pserver_port}")

    #Khởi tạo Node
    assign_global(args.server_ip, args.server_port, args.root_folder, pserver_ip, pserver_port)
    connect_to_tracker()

    server_thread = Thread(target=start_server_process, daemon=False, args=(pserver_ip, pserver_port))
    # CLI_thread = Thread(target=handle_cli_input, daemon=True, args=(pserver_ip, pserver_port))

    server_thread.start()
    # CLI_thread.start()

    #Dọn thread, trả port, disconnect
    signal.signal(signal.SIGINT, cleaning_up)
    signal.signal(signal.SIGTERM, cleaning_up)

    server_thread.join()
    # CLI_thread.join(timeout=1)

    cleaning_up(None, None)
    sys.exit(0)

