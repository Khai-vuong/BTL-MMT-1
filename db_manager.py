import sqlite3

'''Các hàm liên quan đến database'''
def connect_db():
    return sqlite3.connect('tracker.db')

def register_node(peer_ip, peer_port):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Check if the node already exists
        cursor.execute("SELECT COUNT(*) FROM Nodes WHERE ip_address = ? AND port = ?", (peer_ip, peer_port))
        if cursor.fetchone()[0] > 0:
            print(f"Node with IP {peer_ip} and port {peer_port} already exists.")
            return

        # Insert the node if it doesn't exist
        cursor.execute("INSERT INTO Nodes (ip_address, port) VALUES (?, ?)", (peer_ip, peer_port))
        conn.commit()
        print(f"Node with IP {peer_ip} and port {peer_port} registered successfully.")
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

    # Get the file ID based on the file name
    cursor.execute("SELECT fid FROM Files WHERE file_name = ?", (file_name,))
    file = cursor.fetchone()
    if not file:
        print(f"File {file_name} not found.")
        conn.close()
        return

    fid = file[0]

    # Insert the record into the NodesFiles table
    try:
        cursor.execute("INSERT INTO NodesFiles (file_id, node_id) VALUES (?, ?)", (fid, nid))
        conn.commit()
        print(f"Added file {file_name} (fid: {fid}) to node (nid: {nid}).")
    except sqlite3.IntegrityError:
        print(f"File {file_name} (fid: {fid}) is already associated with node (nid: {nid}).")
    finally:
        conn.close()

#Returns (ip, port) of nodes holding the file
def get_nodes_has_file(file_name):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Get the file ID based on the file name
        cursor.execute("SELECT fid FROM Files WHERE file_name = ?", (file_name,))
        file = cursor.fetchone()
        if not file:
            raise ValueError("File not found.")
        
        fid = file[0]

        # Query to find nodes holding the requested file
        cursor.execute("""
            SELECT Nodes.ip_address, Nodes.port 
            FROM NodesFiles
            JOIN Nodes ON NodesFiles.node_id = Nodes.nid
            WHERE NodesFiles.file_id = ?
        """, (fid,))
        nodes = cursor.fetchall()

        if (not nodes):
            raise ValueError("No nodes have the requested file " + file_name + " fid: " + str(fid))

        # Query to find the magnet link and total pieces for the requested file
        cursor.execute("SELECT magnet_link, total_piece FROM Files WHERE fid = ?", (fid,))
        query = cursor.fetchone()

        if query:
            magnet_link, total_piece = query
        else:
            raise ValueError("File not found.")

        return {"nodes": nodes, "magnet_link": magnet_link, "total_piece": total_piece}
    except Exception as e:
        print(f"Error in get_nodes_has_file: {e}")
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

def print_nodes_files():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM NodesFiles")
    print(cursor.fetchall())
    conn.close()