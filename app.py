import os
import hashlib
import sqlite3
import threading
import boto3
from flask import Flask, request, render_template, send_file, jsonify, send_from_directory
from botocore.exceptions import ClientError
from io import BytesIO

app = Flask(__name__)

# --- Configuration ---
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'https://sos-at-vie-1.exo.io') # Default to Exoscale
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY', 'your-access-key')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY', 'your-secret-key')
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-bucket-name')
S3_REGION = os.environ.get('S3_REGION', 'at-vie-1')

MINIMUM_HASH_LENGTH_RETRIEVAL = 40


# Feature Flags
ENABLE_CREATION_ENDPOINT = os.environ.get('ENABLE_CREATION_ENDPOINT', 'False').lower() == 'true'
REQUIRE_HASH = os.environ.get('REQUIRE_HASH', 'False').lower() == 'true'

# File Paths
COUNTER_FILE = 'data/counter.txt'
DB_FILE = 'data/kv_store.db'

# Locks for thread safety
counter_lock = threading.Lock()

# --- Initialization ---

def init_db():
    """Initialize the local Key-Value store (SQLite)"""
    if not os.path.exists('data'):
        os.makedirs('data')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (doc_id INTEGER PRIMARY KEY, hash_string TEXT)''')
    conn.commit()
    conn.close()

def get_s3_client():
    """Returns a configured boto3 client"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION
    )

init_db()

# --- Helper Functions ---

def increment_counter():
    """Reads, increments, and saves the document ID counter from a text file."""
    with counter_lock:
        if not os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'w') as f:
                f.write('0')
        
        with open(COUNTER_FILE, 'r+') as f:
            content = f.read().strip()
            current_id = int(content) if content.isdigit() else 0
            new_id = current_id + 1
            
            f.seek(0)
            f.write(str(new_id))
            f.truncate()
            return new_id

def store_mapping(doc_id, hash_string):
    """Stores the ID -> Hash mapping in the local DB."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO documents (doc_id, hash_string) VALUES (?, ?)", (doc_id, hash_string))
    conn.commit()
    conn.close()

def verify_hash(doc_id, provided_hash):
    """Checks if the provided hash matches the stored hash for the ID."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT hash_string FROM documents WHERE doc_id=?", (doc_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0] == provided_hash:
        return True
    elif result and len(provided_hash) >= MINIMUM_HASH_LENGTH_RETRIEVAL and result[0][:len(provided_hash)] == provided_hash:
        return True
        
    return False

# --- Routes ---
@app.route('/logo.png')
def favicon():
    return send_from_directory('.', 'logo.png')#, mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    """Serves the frontend."""
    return render_template('index.html', require_hash=REQUIRE_HASH, hash_min_length=MINIMUM_HASH_LENGTH_RETRIEVAL)

@app.route('/api/cryptify', methods=['POST'])
def cryptify_text():
    """
    API Endpoint:
    1. Receives text.
    2. Hashes it (SHA256).
    3. Generates new Document ID.
    4. Stores mapping.
    """
    if not ENABLE_CREATION_ENDPOINT:
        return jsonify({"error": "Endpoint disabled"}), 403

    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400

    text_content = data['text']
    
    # Ensure input is a string to avoid AttributeError on .encode()
    if not isinstance(text_content, str):
        text_content = str(text_content)
    
    # 1. Hash the text (SHA256 generates 64 chars)
    hash_object = hashlib.sha256(text_content.encode())
    hash_string = hash_object.hexdigest()

    # 2. Get new ID
    doc_id = increment_counter()

    # 3. Store in KV Store
    store_mapping(doc_id, hash_string)

    return jsonify({
        "document_id": doc_id,
        "hash": hash_string
    })

@app.route('/retrieve', methods=['POST'])
def retrieve_document():
    """
    Web Action:
    1. Validates input.
    2. Checks Hash if required.
    3. Downloads from S3.
    4. Serves to browser.
    """
    doc_id = request.form.get('document_id')
    provided_hash = request.form.get('hash_string', '').strip()

    if not doc_id:
        return "Document ID is required", 400

    # Validation Logic
    if REQUIRE_HASH:
        if not provided_hash:
            return "Hash string is required by system policy.", 403
        
        if not verify_hash(doc_id, provided_hash):
            return "Invalid Document ID or Hash combination.", 403

    # S3 Retrieval
    s3 = get_s3_client()
    file_key = f"{doc_id}.pdf" # Assuming files are named {ID}.pdf in bucket

    try:
        file_obj = s3.get_object(Bucket=S3_BUCKET, Key=file_key)
        file_content = BytesIO(file_obj['Body'].read())
        
        return send_file(
            file_content,
            as_attachment=True,
            download_name=f"{doc_id}.pdf",
            mimetype='application/pdf'
        )

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == "404" or error_code == 'NoSuchKey':
            return "File not found in storage.", 404
        else:
            print(f"S3 Error: {e}")
            return "Error retrieving file from storage.", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
