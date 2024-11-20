import socket
import sqlite3
import json
import sys
import hashlib
import signal

from threading import Thread, Event
from init_db import *
import db_manager as db

#Global
server_socket = None
stop_event = Event()

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

def start_tracker_process(conn, addr):
    client_ip = None
    client_port = None
    
    try:
        while True:
            data = conn.recv(1024).decode("utf-8").strip()
            if not data:  # Nếu không có dữ liệu, ngắt kết nối
                print(f"Connection closed by {addr}")
                break

            print(f"Received from {addr}: {data}")

            # Phân tích và xử lý yêu cầu
            if data.startswith("REGISTER_NODE"):
                _, client_ip, client_port = data.split()
                db.register_node(client_ip, client_port)
                conn.sendall("Node registered!".encode('utf-8'))

            elif data.startswith("REGISTER_FILE"):
                '''
                input REGISTTER_FILE <node_ip> <node_port> <file_name> <total_piece> <magnet_link>
                output: message from the DB
                '''

                _, client_ip, client_port, file_name, total_piece, magnet_link = data.split()                
                response = db.register_file(file_name, int(total_piece), client_ip, client_port, magnet_link)
                conn.sendall(response.encode('utf-8'))

            elif data.startswith("FIND_FILE"):
                '''
                input FIND_FILE <node_ip> <node_port> <file_name>
                output: message from the DB
                '''
                _, client_ip, client_ip, file_name = data.split()
                response = db.get_nodes_has_file(file_name)
                
                # Debug: Print the response from the database
                print(f"Response from the db for file '{file_name}': {response}")
                
                response_json = {
                    "nodes": response["nodes"],
                    "magnet_link": response["magnet_link"],
                    "total_piece": response["total_piece"]
                }
                
                conn.sendall(json.dumps(response_json).encode('utf-8'))

            elif data.startswith("DISCONNECT"):
                _, client_ip, client_port = data.split()
                db.remove_node(client_ip, client_port)
                conn.sendall("Node disconnected.".encode('utf-8'))

            else:
                conn.sendall("Unknown command.".encode('utf-8'))
    except Exception as e:
        print(f"Error in handle_request: {e}")
    finally:
        conn.close()

def handle_cli_input():
    global server_socket
    global stop_event
    try:
        while not stop_event.is_set():
            user_input = input("Tracker CLI > ")

            if user_input.lower() == "exit":
                print("Exiting tracker server...")
                # stop_event.set()
                # server_socket.close()
                # sys.exit(0) 
                signal_handler(0, 0)

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
                elif table_name == "NodesFiles":
                    print("NodesFiles:")
                    print(db.print_nodes_files())
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

def stop_cli_thread():
    print("Stopping CLI thread...")
    sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))

    initialize_database()
    delete_all_data()


    #For CLI debug
    cli_thread = Thread(target=handle_cli_input, daemon=True)
    cli_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((hostip, port))
    server_socket.listen(10)     # Listen at most 10 connections

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        conn, addr = server_socket.accept()      #Lệnh này mang tính blocking, chờ kết nối từ client
        node_thread = Thread(target=start_tracker_process, args=(conn, addr))
        node_thread.start()
