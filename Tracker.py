import socket
import sqlite3
import json
import sys
import hashlib
import signal

from threading import Thread
from init_db import *
import db_manager as db

#Global
server_socket = None

#Lấy IP của máy đang chạy, nếu fail thì lấy IP mặc định = '192.168.56.105'
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

def handle_request(conn, addr):
    try:
        while True:
            data = conn.recv(1024).decode("utf-8").strip()
            if not data:  # Nếu không có dữ liệu, ngắt kết nối
                print(f"Connection closed by {addr}")
                break

            print(f"Received from {addr}: {data}")

            # Phân tích và xử lý yêu cầu
            if data.startswith("REGISTER_NODE"):
                _, peer_ip, peer_port = data.split()
                db.register_node(peer_ip, peer_port)
                conn.sendall("Node registered!".encode('utf-8'))

            elif data.startswith("REGISTER_FILE"):
                '''
                input REGISTTER_FILE <file_name> <total_piece> <magnet_link>
                output: message from the DB
                '''

                _, file_name, total_piece, magnet_link = data.split()
                peer_ip, peer_port = addr[0], addr[1]
                response = db.register_file(file_name, int(total_piece), peer_ip, peer_port, magnet_link)
                conn.sendall(response.encode('utf-8'))


            elif data.startswith("FIND_FILE"):
                _, file_name = data.split()
                response = db.get_nodes_has_file(file_name)
                response_json = {
                    "nodes": response["nodes"],
                    "magnet_link": response["magnet_link"],
                    "total_piece": response["total_piece"]
                }
                conn.sendall(json.dumps(response_json).encode('utf-8'))

            elif data.startswith("DISCONNECT"):
                peer_ip, peer_port = addr[0], addr[1]
                db.remove_node(peer_ip, peer_port)
                conn.sendall("Node disconnected.".encode('utf-8'))

            else:
                conn.sendall("Unknown command.".encode('utf-8'))
    except Exception as e:
        print(f"Error in handle_request: {e}")
    finally:
        conn.close()

def handle_cli_input():
    try:
        while True:
            user_input = input("Tracker CLI > ")
            # Example of handling a command:
            if user_input.lower() == "exit":
                print("Exiting tracker server...")
                server_socket.close()
                sys.exit(0) 

            elif user_input.startswith("DISPLAY"):
                _, table_name = user_input.split()
                if table_name == "Nodes":
                    print("Nodes:")
                    print(db.print_nodes())
                elif table_name == "Files":
                    print("Files:")
                    print(db.print_files())
                elif table_name == "Pieces":
                    print("Pieces:")
                    print(db.print_pieces())
                elif table_name == "PiecesNodes":
                    print("PiecesNodes:")
                    print(db.print_pieces_nodes())
                else:
                    print("Unknown table name.")

            else:
                print(f"Unknown command: {user_input}")
    except Exception as e:
        print(f"Error in handle_cli_input: {e}")

#Handle Ctrl+C
def signal_handler(sig, frame):
    global server_socket
    print('Terminating the server...')
    server_socket.close()
    sys.exit(0)

#Tạo server process, lắng nghe kết nối từ client trên ip:port
def server_program(host, port):
    global server_socket
    server_socket = socket.socket()
    server_socket.bind((host, port))

    server_socket.listen(10)     # Listen at most 10 connections
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    while True:
        conn, addr = server_socket.accept()      #Lệnh này mang tính blocking, chờ kết nối từ client
        node_thread = Thread(target=handle_request, args=(conn, addr))
        node_thread.start()

if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    initialize_database()
    print("Listening on: {}:{}".format(hostip,port))

    #For CLI debug
    cli_thread = Thread(target=handle_cli_input, daemon=True)
    cli_thread.start()

    server_program(hostip, port)

'''
    data.split() -> ['REGISTER_FILE', 'file_name', 'total_piece'], nó trả về array
    command, file_name, total_piece = data.split() tức gán từng phần tử

    ký tự _ để chỉ ra phần tử không cần thiết
'''