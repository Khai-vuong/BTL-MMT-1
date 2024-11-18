import sqlite3

'''Các hàm liên quan đến database'''
def connect_db():
    return sqlite3.connect('tracker.db')

def register_node(peer_ip, peer_port):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Nodes (ip_address, port) VALUES (?, ?)", (peer_ip, peer_port))
        conn.commit()
    except Exception as e:
        print(f"Error in register_node: {e}")
    finally:
        conn.close()

def remove_node(peer_ip, peer_port):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Nodes WHERE ip_address = ? AND port = ?", (peer_ip, peer_port))
        conn.commit()
    except Exception as e:
        print(f"Error in remove_node: {e}")
    finally:
        conn.close()


def register_file(file_name, total_piece, node_ip, node_port, magnet_link):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Kiểm tra file đã tồn tại chưa
        cursor.execute("SELECT COUNT(*) FROM Files WHERE file_name = ?", (file_name,))
        if cursor.fetchone()[0] > 0:
            return "File already exists."

        # Thêm file mới vào bảng Files
        cursor.execute('''
        INSERT INTO Files (file_name, total_piece, magnet_link) 
        VALUES (?, ?, ?)
        ''', (file_name, total_piece, magnet_link))
        conn.commit()

        # Tìm node ID dựa trên IP và port
        cursor.execute("SELECT nid FROM Nodes WHERE ip_address = ? AND port = ?", (node_ip, node_port))
        node = cursor.fetchone()
        if not node:
            return "Node not found."

        nid = node[0]
        add_file_to_node(nid, file_name)

        return "File registered and added to the node!"
    except Exception as e:
        print(f"Error in register_file: {e}")
        return "Error registering file."
    finally:
        conn.close()


def add_file_to_node(nid, file_name):
    conn = connect_db()
    cursor = conn.cursor()

    # Lấy giá trị hiện tại
    cursor.execute("SELECT files_holding FROM Nodes WHERE nid = ?", (nid,))
    result = cursor.fetchone()      #Result is a tuple
    if result:
        files_holding = result[0].split(",") if result[0] else []
        if file_name not in files_holding:
            files_holding.append(file_name)
            # Cập nhật giá trị
            cursor.execute("UPDATE Nodes SET files_holding = ? WHERE nid = ?", (",".join(files_holding), nid))
    conn.commit()
    conn.close()

#Returns (ip, port) of nodes holding the file
def get_nodes_has_file(file_name):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address, port FROM Nodes WHERE files_holding LIKE ?", ('%'+file_name+'%',))
        nodes = cursor.fetchall()
    
        cursor.execute("SELECT magnet_link, total_piece FROM Files WHERE file_name = ?", (file_name,))
        query = cursor.fetchone()

        if query:
            magnet_link, total_piece = query
        else:
            raise ValueError("File not found.")

        return {"nodes": nodes, "magnet_link": magnet_link, "total_piece": total_piece}
    except Exception as e:
        print(f"Error in get_node_has_file: {e}")
    finally:
        conn.close()

'''DEBUG FUNCTIONS'''
def print_nodes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Nodes")
    print(cursor.fetchall())
    conn.close()

def print_files():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Files")
    print(cursor.fetchall())
    conn.close()

def print_pieces():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pieces")
    print(cursor.fetchall())
    conn.close()

def print_pieces_nodes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PiecesNodes")
    print(cursor.fetchall())
    conn.close()