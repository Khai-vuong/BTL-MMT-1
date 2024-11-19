import sqlite3

def initialize_database(db_name="tracker.db"):
    """
    Initializes the database with necessary tables for the P2P tracker.

    Args:
        db_name (str): Name of the SQLite database file.
    """
    # Connect to the database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()


    # Create the Nodes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Nodes (
        nid INTEGER PRIMARY KEY,
        ip_address TEXT NOT NULL,
        port INTEGER NOT NULL
    )
    ''')

    # Create the Files table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Files (
        fid INTEGER PRIMARY KEY,
        file_name TEXT NOT NULL,
        total_piece INTEGER NOT NULL,
        magnet_link TEXT
    )
    ''')

    # Create the Pieces table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Pieces (
        pid INTEGER PRIMARY KEY,
        file_id INTEGER NOT NULL,
        piece_index INTEGER NOT NULL,
        node_having INTEGER,
        FOREIGN KEY (file_id) REFERENCES Files(fid)
    )
    ''')

    # Create the PiecesNodes table to support the N-M relationship
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PiecesNodes (
        piece_id INTEGER NOT NULL,
        node_id INTEGER NOT NULL,
        PRIMARY KEY (piece_id, node_id),
        FOREIGN KEY (piece_id) REFERENCES Pieces(pid),
        FOREIGN KEY (node_id) REFERENCES Nodes(nid)
    )
    ''')


    cursor.execute('''
    CREATE TABLE IF NOT EXISTS NodesFiles (
        file_id INTEGER NOT NULL,
        node_id INTEGER NOT NULL,
        PRIMARY KEY (file_id, node_id),
        FOREIGN KEY (file_id) REFERENCES Files(fid),
        FOREIGN KEY (node_id) REFERENCES Nodes(nid)
    )
    ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print(f"Database '{db_name}' has been initialized!")

# Main block to trigger the initialization
if __name__ == "__main__":
    initialize_database()