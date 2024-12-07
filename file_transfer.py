import os
import hashlib
import socket
import json
import threading
import urllib.parse
from time import sleep

import concurrent.futures
PIECESIZE = 1024

'''
Debug functions
'''
def inscpect(obj):
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2))
    else:
        print(type(obj))
        print(obj)

'''
Socket related functions
'''
def get_ephemeral_socket(Node_ip, Node_port):
    """
    Establish a connection to a Node using an ephemeral port.
    :return: A connected socket object.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(("", 0))  # Bind to an ephemeral port
    client_socket.connect((Node_ip, Node_port))
    client_socket.settimeout(20)
    return client_socket


'''
Not yet touched (IDK what it does)
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

def decode_magnet_link(magnet_link):        # Terminated
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise ValueError("Invalid magnet link format.")

    parsed_url = urllib.parse.urlparse(magnet_link)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Extract the info_hash and file_name (dn)
    info_hash = parsed_url.path.split(":")[-1]
    file_name = query_params.get("dn", ["Unknown"])[0]

    return {"info_hash": info_hash, "file_name": file_name}

def split_file(file_name, piece_size=PIECESIZE):  # Default piece size = 1 MB
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


'''
File related functions
'''
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

def parse_find_file_response(response):
    """
    Input: A JSON string containing the response from the tracker.
    Returns:
        dict: A dictionary (JSON object) containing the nodes, magnet_link, and total_pieces.
    """
    try:
        response_json = json.loads(response)  # Parse the JSON response
        nodes = response_json.get("nodes", [])
        magnet_link = response_json.get("magnet_link")
        total_piece = response_json.get("total_piece")

        print(f"Nodes: {nodes}")
        print(f"Magnet link: {magnet_link}")
        print(f"Total pieces: {total_piece}")

        if isinstance(nodes, list) and nodes:
            print("Nodes with the requested file:")
            for node in nodes:
                ip = node[0]
                port = node[1]
                print(f"Node: {ip}:{port}")
        else:
            print("No nodes have the requested file.")

        return {
            "nodes": nodes,
            "magnet_link": magnet_link,
            "total_piece": total_piece
        } #Học thêm về python JSON
    except json.JSONDecodeError:
        print("Error decoding server response. Raw response:")
        print(response)
        return None

def download_piece(piece_index, peer_ip, peer_port, file_name, save_path):
    """
    Tải một mảnh từ peer.
    """
    download_socket = get_ephemeral_socket(peer_ip, peer_port)
    try:
        print(f"Downloading piece {piece_index} from {peer_ip}:{peer_port}...")


        # Yêu cầu mảnh từ peer
        request = f"REQUEST_PIECE {file_name} {piece_index}"
        download_socket.sendall(request.encode('utf-8'))
        
        # Nhận dữ liệu mảnh
        piece_data = download_socket.recv(PIECESIZE)  # Dự phòng thêm 20 byte cho header
        if not piece_data:
            print(f"Failed to download piece {piece_index} from {peer_ip}:{peer_port}")
            return False
        
        # Lưu mảnh vào file tạm
        piece_path = os.path.join(save_path, f"{file_name}.part{piece_index}")
        with open(piece_path, "wb") as f:
            f.write(piece_data)
        
        print(f"Successfully downloaded piece {piece_index} from {peer_ip}:{peer_port}")
        sleep(0.3)  # Delay to prevent spamming the console

        return True
    
    except socket.timeout:
        print("Timeout: Không nhận được dữ liệu trong 5 giây.")

    except Exception as e:
        print(f"Error downloading piece {piece_index} from {peer_ip}:{peer_port}: {e}")
        return False
    finally:
        download_socket.close()

def download_file(file_name, nodes, magnet_link, total_pieces, save_path="downloads"):
    """
    Tải toàn bộ file từ danh sách các nodes được cung cấp.
    Inputs:
        file_name (str):
        nodes (list): eg: [["192.168.56.104", 1100], ["192.168.56.106", 1100]]
        magnet_link (str): 
        total_pieces (int): 
        save_path (str):
    """
    # Kiểm tra nếu file đã tồn tại
    file_path = os.path.join(save_path, file_name)
    if os.path.exists(file_path):
        print(f"I already have file {file_path}")
        return False
    

    os.makedirs(save_path, exist_ok=True)

    # Tải từng mảnh
    threads = []
    total_nodes = len(nodes)  # Tổng số nodes

    for piece_index in range(total_pieces):
        # Tính toán node sử dụng theo công thức (piece_index % total_nodes)
        node_index = piece_index % total_nodes
        peer_ip = nodes[node_index][0]
        peer_port = nodes[node_index][1]
        
        # Tạo và khởi động thread cho từng piece
        thread = threading.Thread(
            target=download_piece,
            args=(piece_index, peer_ip, peer_port, file_name, save_path)
        )
        threads.append(thread)
        thread.start()

    # Chờ tất cả các luồng tải xong
    for thread in threads:
        thread.join()

    # Kết hợp các mảnh lại thành file hoàn chỉnh
    file_path = os.path.join(save_path, file_name)
    with open(file_path, "wb") as output_file:
        for piece_index in range(total_pieces):
            piece_path = os.path.join(save_path, f"{file_name}.part{piece_index}")

            # Đọc mảnh và ghi vào file hoàn chỉnh
            if os.path.exists(piece_path):
                with open(piece_path, "rb") as piece_file:
                    output_file.write(piece_file.read())
                os.remove(piece_path)  # Delete the piece after combining

            #M Piece tải không thành công. Phần này Sync
            else:
                print(f"Piece {piece_index} is missing. Retrying download...")
                success = False
                for _ in range(3):  # Retry up to 3 times
                    node_index = piece_index % total_nodes
                    peer_ip = nodes[node_index][0]
                    peer_port = nodes[node_index][1]
                    success = download_piece(piece_index, peer_ip, peer_port, file_name, save_path)
                    if success:
                        break
                if not success:
                    print(f"Failed to download piece {piece_index} after multiple attempts.")
                    return False

    #Validate the file via magnet_link
    pieces_metadata = split_file(file_path)
    downloaded_magnet_link = generate_magnet_link(file_name, pieces_metadata)

    if downloaded_magnet_link != magnet_link:
        print("Downloaded file is corrupted. Deleting...")
        print(f"Expected magnet link: {magnet_link}")
        print(f"Actual magnet link: {downloaded_magnet_link}")
        os.remove(file_path)
        return False

    print(f"Download completed! File saved at: {file_path}")
    return True
    
def upload_piece(root_folder, upload_socket, file_name, piece_index, piece_size=1024):
    """
    Upload a specific piece of a file (in bits) to the client.
    
    Args:
        root_folder (str): The root folder where the file pieces are stored.
        client_socket (socket): The client socket to send the piece to.
        file_name (str): The name of the file.
        piece_index (int): The index of the piece to upload.
        piece_size (int): The size of each piece in bytes (default is 1024 bytes).
    
    Returns:
        bool: True if the piece was successfully uploaded, False otherwise.
    """
    try:
        file_path = os.path.join(root_folder, file_name)
        if not os.path.isfile(file_path):
            upload_socket.sendall(f"File {file_name} not found.".encode('utf-8'))
            return False

        # Calculate the byte range for the piece
        start_byte = piece_index * piece_size

        with open(file_path, "rb") as file:
            file.seek(start_byte)
            piece_data = file.read(piece_size)

        if not piece_data:
            upload_socket.sendall(f"Piece {piece_index} is out of range for file {file_name}.".encode('utf-8'))
            return False

        # Send the piece data to the client
        upload_socket.sendall(piece_data)
        print(f"Successfully uploaded piece {piece_index} of file {file_name}.")
        return True

    except Exception as e:
        print(f"Error uploading piece {piece_index} of file {file_name}: {e}")
        return False