import socket

def start_client(host='192.168.56.105', port=12345):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")

        message = "Hello, Server!"
        client_socket.sendall(message.encode())
        print(f"Sent to server: {message}")

        data = client_socket.recv(1024)
        print(f"Received from server: {data.decode()}")

        print("Connection closed")

if __name__ == "__main__":
    start_client()