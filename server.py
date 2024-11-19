import socket
from threading import Thread

def handle_client(conn, addr):
    """
    Xử lý giao tiếp với một client.
    """
    print(f"Connected by {addr}")
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Received from client: {data.decode()}")
            response = f"Server received: {data.decode()}"
            conn.sendall(response.encode())
        print(f"Connection with {addr} closed")

def start_server(host='192.168.56.105', port=12345):
    """
    Khởi động server hỗ trợ nhiều client đồng thời.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Server listening on {host}:{port}")

        while True:
            conn, addr = server_socket.accept()
            thread = Thread(target=handle_client, args=(conn, addr))
            thread.start()  # Bắt đầu một luồng mới để xử lý client
            print(f"Thread started for {addr}")

if __name__ == "__main__":
    start_server()
