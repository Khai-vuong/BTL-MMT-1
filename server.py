import socket
from threading import Thread

peer_list = []

def new_connection(addr, conn):
    add_list(conn)
    receive_message(conn)

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

def add_list(data):
    global peer_list
    peer_list.append(data)
    print(f"Added peer: {data}")

def get_list():
    global peer_list
    return str(peer_list)

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

        if data.startswith('GET_LIST'):
            respone = str(peer_list)
            conn.sendall(respone.encode())

        if data.startswith('HELLO'):
            _, addr = data.split()
            add_list(addr)
            respone = get_list()
            conn.sendall(respone.encode())
        
        print("From connected user: " + str(data))
    conn.close()

if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)
