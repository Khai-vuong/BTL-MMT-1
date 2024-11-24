import socket
import argparse
from threading import Thread


def peer_connect(ip, port):
    # Kết nối tới một peer khác
    try:
        peer_socket = socket.socket()
        peer_socket.connect((ip, port))
        print(f"Connected to peer {ip}:{port}")
        return peer_socket
    except Exception as e:
        print(f"Failed to connect to peer {ip}:{port}: {e}")
        return None


def peer_transfer(peer_socket, data):
    # Truyền dữ liệu tới peer đã kết nối
    try:
        peer_socket.send(data.encode())
        print("Data sent to peer:", data)
    except Exception as e:
        print("Failed to send data:", e)
    finally:
        peer_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Peer-to-Peer Client',
        description='Connect and transfer data to another peer')

    parser.add_argument('--peer-ip', required=True,
                        help="IP of peer to connect to")
    parser.add_argument('--peer-port', type=int, required=True,
                        help="Port of peer to connect to")
    parser.add_argument('--data', required=True,
                        help="Data to transfer to peer")

    args = parser.parse_args()
    peer_ip = args.peer_ip
    peer_port = args.peer_port
    data = args.data

    # Kết nối tới peer
    peer_socket = peer_connect(peer_ip, peer_port)
    if peer_socket:
        # Truyền dữ liệu nếu kết nối thành công
        peer_transfer(peer_socket, data)
