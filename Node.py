import socket
import argparse
import json
import os
import concurrent.futures
import hashlib
import threading
import urllib.parse

from threading import Thread

PIECESIZE = 1024
client_socket = None

'''
Các Hàm về kết nối tracker (initialize)
'''
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

        # Register the node immediately after connection
        register_node(client_socket, node_ip, node_port)
        return client_socket

    except socket.error as e:
        print(f"Error connecting to server: {e}")
        return None

def register_node(client_socket, ip, port):
    try:
        message = f"REGISTER_NODE {ip} {port}"
        client_socket.sendall(message.encode())
        print(f"Sent registration message: {message}")

        respone = client_socket.recv(1024).decode("utf-8")
        print(f"Server response: {respone}")
    except socket.error as e:
        print(f"Error sending registration message: {e}")

'''
Các hàm về download / upload file
'''
def generate_magnet_link(file_name, pieces_metadata):
    """
    Generates a magnet link for a file based on its metadata.

    Args:
        file_name (str): Name of the file.
        pieces_metadata (list): Metadata of all pieces (list of hashes or similar info).

    Returns:
        str: Magnet link for the file.
    """
    # Concatenate piece hashes to compute the file's info_hash
    info_hash = hashlib.sha1("".join(p['piece_hash'] for p in pieces_metadata).encode()).hexdigest()

    # Build the magnet link
    magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={file_name}"
    return magnet_link

def decode_magnet_link(magnet_link):
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise ValueError("Invalid magnet link format.")

    parsed_url = urllib.parse.urlparse(magnet_link)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Extract the info_hash and file_name (dn)
    info_hash = parsed_url.path.split(":")[-1]
    file_name = query_params.get("dn", ["Unknown"])[0]

    return {"info_hash": info_hash, "file_name": file_name}

def split_file(file_name, piece_size=1024 * 1024):  # Default piece size = 1 MB
    """
    Splits a file into pieces and generates metadata for each piece.

    Args:
        file_name (str): Name of the file to be split.
        piece_size (int): Size of each piece in bytes.

    Returns:
        list: Metadata of pieces, including hashes and indices.
    """
    file_path = os.path.join(os.getcwd(), file_name)  # Construct file path in the current directory

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    total_pieces = (file_size + piece_size - 1) // piece_size  # Calculate number of pieces
    
    metadata = []  # Store metadata for each piece
    with open(file_path, "rb") as f:
        for index in range(total_pieces):
            piece_data = f.read(piece_size)
            piece_hash = hashlib.sha256(piece_data).hexdigest()  # Generate piece hash
            metadata.append({
                "file_name": file_name,
                "piece_index": index,
                "piece_hash": piece_hash
            })
    
    return metadata

def find_file(tracker_ip, tracker_port, file_name):
    """
    Returns:
        dict: A dictionary containing the nodes, magnet_link, and total_pieces.
    """
    try:
        # Create and connect the socket to the tracker
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((tracker_ip, tracker_port))

        # Send FIND_FILE request
        request = f"FIND_FILE {file_name}"
        client_socket.sendall(request.encode())
        print(f"Sent request: {request}")

        # Receive and parse the response
        response = client_socket.recv(4096).decode("utf-8")
        response_json = json.loads(response)
        return response_json

    except socket.error as e:
        print(f"Error connecting to tracker: {e}")
        return None

    finally:
        client_socket.close()

def download_piece(piece_index, peer_ip, peer_port, file_name, save_path):
    """
    Tải một mảnh từ peer.
    """
    client_socket.settimeout(5)  # Timeout sau 5 giây nếu không nhận được dữ liệu
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((peer_ip, peer_port))
        
        # Yêu cầu mảnh từ peer
        request = f"REQUEST_PIECE {file_name} {piece_index}"
        client_socket.sendall(request.encode())
        
        # Nhận dữ liệu mảnh
        piece_data = client_socket.recv(PIECESIZE)  # Blocking function, chờ cho đến khi nhận được dữ liệu
        if not piece_data:
            print(f"Failed to download piece {piece_index} from {peer_ip}:{peer_port}")
            return False
        
        # Lưu mảnh vào file tạm
        piece_path = os.path.join(save_path, f"{file_name}.part{piece_index}")
        with open(piece_path, "wb") as f:
            f.write(piece_data)
        
        print(f"Successfully downloaded piece {piece_index} from {peer_ip}:{peer_port}")
        return True
    
    except socket.timeout:
        print("Timeout: Không nhận được dữ liệu trong 5 giây.")

    except Exception as e:
        print(f"Error downloading piece {piece_index} from {peer_ip}:{peer_port}: {e}")
        return False
    finally:
        client_socket.close()

def download_file(file_name, nodes, magnet_link, total_pieces, save_path="downloads"):
    """
    Tải toàn bộ file từ danh sách các nodes được cung cấp.
    """
    os.makedirs(save_path, exist_ok=True)

    # Tải từng mảnh
    threads = []
    for piece_index in range(total_pieces):
        for node in nodes:
            peer_ip = node["ip"]
            peer_port = node["port"]
            thread = threading.Thread(
                target=download_piece,
                args=(piece_index, peer_ip, peer_port, file_name, save_path)
            )
            threads.append(thread)
            thread.start()
            break  # Chỉ sử dụng 1 peer cho mỗi mảnh ở đây (có thể tối ưu hơn)

    # Chờ tất cả các luồng tải xong
    for thread in threads:
        thread.join()

    # Kết hợp các mảnh lại thành file hoàn chỉnh
    file_path = os.path.join(save_path, file_name)
    with open(file_path, "wb") as output_file:
        for piece_index in range(total_pieces):
            piece_path = os.path.join(save_path, f"{file_name}.part{piece_index}")
            with open(piece_path, "rb") as piece_file:
                output_file.write(piece_file.read())
            os.remove(piece_path)  # Xóa mảnh sau khi ghép xong

    print(f"Download completed! File saved at: {file_path}")


def send_runtime_commands(client_socket : socket.socket):
    print("You can now enter runtime commands. Type 'exit' to quit.")

    try:
        while True:
            command = input("Node CLI >")
            if command.lower() == "exit":
                print("Closing connection...")
                client_socket.sendall("DISCONNECT".encode())
                break

            elif command.startwith("REGISTTER_FILE"):
                '''
                REGISTTER_FILE <file_name> <total_piece> <magnet_link>
                '''
                try:
                    file_path = command.split(" ", 1)[1]  # Extract file path from command
                    pieces_metadata = split_file(file_path)  # Split the file and get metadata

                    magnet_link = generate_magnet_link(os.path.basename(file_path), pieces_metadata)
                    request = f"{command} {magnet_link}"  
                    client_socket.sendall(request.encode())  
                    print(f"Sent request: {request}")
                except Exception as e:
                    print(f"Error processing REGISTER_FILE command: {e}")

            elif command.startswith("FIND_FILE"):
                client_socket.sendall(command.encode())  # Send FIND_FILE command
                
                # Receive and parse server response
                response = client_socket.recv(1024).decode()
                try:
                    response_json = json.loads(response)  # Parse the JSON response
                    nodes = response_json.get("nodes", [])
                    magnet_link = response_json.get("magnet_link")


                    nodes = json.loads(response)  # Parse the JSON response
                    if isinstance(nodes, list) and nodes:
                        print("Nodes with the requested file:")
                        for node in nodes:
                            ip = node.get("ip", "Unknown IP")
                            port = node.get("port", "Unknown Port")
                            print(f"Node: {ip}:{port}")
                    else:
                        print("No nodes have the requested file.")
                except json.JSONDecodeError:
                    print("Error decoding server response. Raw response:")
                    print(response)


            # Wait for server response
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")
    except Exception as e:
        print(f"Error in runtime commands: {e}")
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

    args = parser.parse_args()

    # Extract arguments
    server_ip = args.server_ip
    server_port = args.server_port
    client_ip, client_port = get_default_interface() # Automatically detect the node's IP

    print(f"Node IP detected: {client_ip}")
    print(f"Node Port specified: {client_port}")


    # Establish connection to the server and register the node
    client_socket = connect_to_tracker(server_ip, server_port, client_ip, client_port)
    if client_socket:
        send_runtime_commands(client_socket)  # Keep the connection and CLI open
        client_socket.close()  # Close the connection when done
        print("Connection closed.")