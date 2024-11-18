import hashlib
import urllib.parse

def generate_magnet_link(file_name, pieces_metadata):
    """
    Generates a magnet link for a file based on its metadata.

    Args:
        file_name (str): Name of the file.
        pieces_metadata (list): Metadata of all pieces (list of hashes or similar info).

    Returns:
        str: Magnet link for the file.
    """
    # Concatenate piece hashes to compute the file's info_hash
    info_hash = hashlib.sha1("".join(p['piece_hash'] for p in pieces_metadata).encode()).hexdigest()

    # Build the magnet link
    magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={file_name}"
    return magnet_link

def decode_magnet_link(magnet_link):
    """
    Decodes a magnet link to extract the info_hash and file_name.

    Args:
        magnet_link (str): The magnet link to decode.

    Returns:
        dict: A dictionary containing the info_hash and file_name.
    """
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise ValueError("Invalid magnet link format.")

    parsed_url = urllib.parse.urlparse(magnet_link)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Extract the info_hash and file_name (dn)
    info_hash = query_params.get("xt", [""])[0].split(":")[-1]
    file_name = query_params.get("dn", ["Unknown"])[0]

    return {"info_hash": info_hash, "file_name": file_name}

if __name__ == "__main__":
    metadata = [
        {
            "file_name": "example_file.txt",
            "piece_index": 0,
            "piece_hash": "aaaa"
        },
        {
            "file_name": "example_file.txt",
            "piece_index": 1,
            "piece_hash": "bbbb"
        },
        {
            "file_name": "example_file.txt",
            "piece_index": 2,
            "piece_hash": "cccc"
        },
        {
            "file_name": "example_file.txt",
            "piece_index": 3,
            "piece_hash": "dddd"
        }
    ]

    magnet = generate_magnet_link("example_file.txt", metadata)
    hashed = decode_magnet_link(magnet)
    