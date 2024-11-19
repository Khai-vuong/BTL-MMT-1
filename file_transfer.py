import os
import hashlib
import socket
import json
import threading
import urllib.parse

import concurrent.futures
PIECESIZE = 1024


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
    Returns:
        dict: A dictionary containing the nodes, magnet_link, and total_pieces.
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

        return response_json
    except json.JSONDecodeError:
        print("Error decoding server response. Raw response:")
        print(response)
        return None

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

