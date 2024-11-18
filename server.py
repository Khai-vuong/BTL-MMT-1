import socket
from threading import Thread


def new_connection(addr, conn):
    data = conn.recv(1024).decode("utf-8")
    # print(data)       # data is the peer info
    # add_list(data)
    print(addr)

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '192.168.56.105'    # default IP
    finally:
       s.close()
    return ip

def add_list(serversocket, peer_ip, peer_port):
    data, addr = serversocket.recvfrom(1024)
    peer_info = data.decode("utf-8")
    print(f"Added peer: {peer_info}")


def server_program(host, port):
    serversocket = socket.socket()
    serversocket.bind((host, port))

    serversocket.listen(10)
    while True:
        conn, addr = serversocket.accept()
        nconn = Thread(target=new_connection, args=(addr, conn))
        nconn.start()

def receive_message(conn):
    while True:
        data = conn.recv(1024).decode()
        if not data:
            break
        print("From connected user: " + str(data))
    conn.close()

if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)
