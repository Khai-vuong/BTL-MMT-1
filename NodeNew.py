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
        s.connect(("8.8.8.8", 1))  # Simulate a connection to get the IP
        ip = s.getsockname()[0]
        port = 1100  # Default port
    except Exception:
        ip, port = "192.168.56.104", 200
    finally:
        s.close()
    return ip, port

def get_ephemeral_socket():
    """
    Establish a connection TO THE TRACKER using an ephemeral port.
    :return: A connected socket object.
    """
    global tracker_ip, tracker_port

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(("", 0))  # Bind to an ephemeral port
    client_socket.connect((tracker_ip, tracker_port))
    client_socket.settimeout(10)
    return client_socket

# def get_ephemeral_socket(ip, port):
#     """
#     Establish a connection to the targeted peer using an ephemeral port.
#     """
#     client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     client_socket.bind(('', 0))
#     client_socket.connect((ip, port))
#     client_socket.settimeout(10)
#     return client_socket

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
    ephemeral_socket = get_ephemeral_socket()

    try:        
        register_node(ephemeral_socket)
        register_files(ephemeral_socket)

    except Exception as e:
        print(f"Error connecting to tracker: {e}")

    finally:
        if ephemeral_socket:
            ephemeral_socket.close()

# Thread-related functions
def start_server_process(this_ip, this_port):   #terminated
    """
    Start a server process that continuously listens for incoming connections.
    :param ip: IP address to bind the server to.
    :param port: Port to bind the server to.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((this_ip, this_port))
    server_socket.listen(5)

    print(f"Node listening on {this_ip}:{this_port}")
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
    global root_path
    try:
        while not stop_server.is_set():
            data = client_conn.recv(1024).decode("utf-8").strip()
            if not data:
                print("Client disconnected.")
                break

            print(f"Received from client: {data}") # Có thể bỏ
            if data.startswith("REQUEST_PIECE"):
                '''
                REQUEST_PIECE <file_name> <piece_index>
                '''
                _, file_name, piece_index = data.split()
                f_sys.upload_piece(root_path, client_conn, file_name, int(piece_index))


    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_conn.close()
    
def handle_cli_input(this_ip, this_port):
    # Bind to an ephemeral port
    print("You can now enter runtime commands. Type 'exit' to quit.")
    global root_path

    while True:
        command = input("Node CLI >")

        try:
            if command.lower() == "exit":
                stop_server.set()
                print("Closing connection...")
                break    

            elif command.startswith("FIND_FILE"):       
                '''
                FIND_FILE <file_name>
                '''         
                try:
                    client_socket = get_ephemeral_socket()
                    _, file_name = command.split()
                    request = command
                    client_socket.sendall(request.encode('utf-8'))
                    print(f"Sent request: {request}")

                    response = client_socket.recv(1024 * 20).decode('utf-8')
                    respone_json = f_sys.parse_find_file_response(response)
                    print(f"Server response: ")
                    f_sys.inscpect(respone_json)

                except Exception as e:
                    print(f"Error processing FIND_FILE command: {e}")
                finally:
                      client_socket.close()

            elif command.startswith("REQUEST_FILE"):
                '''
                REQUEST_FILE <file_name>
                '''    
                try:
                    client_socket = get_ephemeral_socket()
                    _, file_name = command.split()
                    request = f"FIND_FILE {file_name}"

                    client_socket.sendall(request.encode('utf-8'))
                    print(f"Sent request: {request}")

                    response = client_socket.recv(1024 * 20).decode('utf-8')
                    respones_json = f_sys.parse_find_file_response(response)
                    print('JSON object retrived')

                    f_sys.inscpect(respones_json)

                    nodes = respones_json['nodes']                  #Array of [ip, port], eg: [["192.168.56.104", 1100], ["192.168.56.106", 1100]]
                    magnet_link = respones_json['magnet_link']      #String
                    total_piece = respones_json['total_piece']      #Int

                    f_sys.download_file(file_name, nodes, magnet_link, total_piece, root_path)

                    #Declare new file to the tracker
                    register_files(get_ephemeral_socket()) #Maybe register already have files.


                except Exception as e:
                    print(f"Error processing REQUEST_FILE command: {e}")
                finally:
                    client_socket.close()

        except Exception as e:
            print(f"Error in runtime commands: {e}")

#Cleaning up functions
def cleaning_up(sig, frame):
    global stop_server
    stop_server.set()
    print("Interrupt received, shutting down...")

    ephemeral_socket = get_ephemeral_socket()
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
    # parser.add_argument("--server-ip", required=True, help="IP address of the server.")
    # parser.add_argument("--server-port", type=int, required=True, help="Port of the server.")
    parser.add_argument("--root-folder", required=True, help="Root folder.")

    args = parser.parse_args()

    # Extract arguments
    # tracker_ip = args.server_ip
    # tracker_port = args.server_port

    tracker_ip = '192.168.56.105'
    tracker_port = 22236

    #personal IP and port (this_ip, this_port)
    pserver_ip, pserver_port = get_default_interface()  # Automatically detect the node's IP

    print(f"Node IP detected: {pserver_ip}")
    print(f"Node Port specified: {pserver_port}")

    #Khởi tạo Node
    assign_global(tracker_ip, tracker_port, args.root_folder, pserver_ip, pserver_port)
    connect_to_tracker()

    # server_thread = Thread(target=start_server_process, daemon=False, args=(pserver_ip, pserver_port))
    CLI_thread = Thread(target=handle_cli_input, daemon=True, args=(pserver_ip, pserver_port))

    # server_thread.start()
    CLI_thread.start()

    #Dọn thread, trả port, disconnect
    signal.signal(signal.SIGINT, cleaning_up)
    signal.signal(signal.SIGTERM, cleaning_up)

    # server_thread.join()
    # CLI_thread.join()

    #Try this model! the server model as the main thread, and the CLI as the sub-thread (daemon)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((pserver_ip, pserver_port))
    server_socket.listen(35)

    print(f"Node listening on {this_ip}:{this_port}")

    while True:
        print("Waiting for connection...")
        conn, addr = server_socket.accept()      #Lệnh này mang tính blocking, chờ kết nối từ client
        node_thread = Thread(target=handle_income_request, args=(conn,))
        node_thread.start()
        node_thread.join()
        

    cleaning_up(None, None)
    sys.exit(0)

