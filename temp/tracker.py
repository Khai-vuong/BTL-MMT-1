import socket
from threading import Thread

peer_list = []


def add_list(peer_ip, peer_port):
    # Thêm thông tin của peer vào danh sách
    peer_info = (peer_ip, peer_port)
    if peer_info not in peer_list:
        peer_list.append(peer_info)
    print("Updated Peer List:", peer_list)


def get_list(conn):
    # Gửi danh sách peer tới client
    peer_data = "\n".join([f"{ip}:{port}" for ip, port in peer_list])
    conn.sendall(peer_data.encode())


def new_connection(addr, conn):
    # Nhận dữ liệu từ client và thêm vào danh sách hoặc gửi danh sách nếu client yêu cầu
    data = conn.recv(1024).decode()
    if data == "get_list":  # Nếu client yêu cầu danh sách
        get_list(conn)
    else:  # Nếu là dữ liệu peer gửi tới
        peer_ip, peer_port = data.split(":")
        add_list(peer_ip, int(peer_port))
    conn.close()


def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '192.168.56.103'
    finally:
        s.close()
    return ip


def server_program(host, port):
    serversocket = socket.socket()
    serversocket.bind((host, port))
    serversocket.listen(10)
    print("Server listening on {}:{}".format(host, port))

    while True:
        conn, addr = serversocket.accept()
        Thread(target=new_connection, args=(addr, conn)).start()


if __name__ == "__main__":
    hostip = get_host_default_interface_ip()
    port = 22236
    server_program(hostip, port)
