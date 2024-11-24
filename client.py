import socket
import time
import argparse
import ast


from threading import Thread
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
        ip, port = "192.168.56.102", 10000
    finally:
        s.close()
    return ip, port

def get_list(data):
    return data

def connect_peer(peer_ip, peer_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(("", 0))
    client_socket.connect((peer_ip, peer_port))
    return client_socket

def connect_server(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   
    client_socket.bind(("192.168.56.102", 10000))
    client_socket.connect((host, port))

    this_ip = get_default_interface()[0]
    this_port = get_default_interface()[1]

    request1 = f'HELLO {this_ip}:{this_port}'
    client_socket.sendall(request1.encode())

    response1 = client_socket.recv(1024).decode()

    _, me = request1.split()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog='Client',
                        description='Connect to pre-declard server',
                        epilog='!!!It requires the server is running and listening!!!')
    parser.add_argument('--server-ip')
    parser.add_argument('--server-port', type=int)
    args = parser.parse_args()
    host = args.server_ip
    port = args.server_port
    connect_server(host, port)
