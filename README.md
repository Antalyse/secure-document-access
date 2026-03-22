# Secure Document Access

![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

A Flask-based application for secure document management with SHA256 hash-based access control and S3 storage integration.

## Overview

Secure Document Access is a web application that provides a secure method for storing, retrieving, and sharing documents with optional cryptographic hash-based verification. Documents are stored on S3-compatible storage, and access is controlled through document IDs and optional hash verification.

## Key Features

- **Document Cryptification**: Generate SHA256 hashes for text content and assign unique document IDs
- **Hash-Based Access Control**: Optional verification using document ID and hash combinations
- **S3 Integration**: Seamless integration with S3-compatible storage backends (tested with Exoscale)
- **Thread-Safe Operations**: Safe concurrent access with SQLite-backed ID counter and mapping storage
- **Configurable Feature Flags**: Enable/disable document creation and hash verification via environment variables
- **Docker Support**: Full Docker and Docker Compose support for easy deployment
- **Partial Hash Matching**: Support for shortened hash values (minimum 40 characters) for convenience

## Architecture

The application consists of three main components:

1. **Web Frontend** (`templates/index.html`): User interface for document retrieval
2. **Flask Backend** (`app.py`): REST API and business logic
3. **Storage Backend**: S3 bucket for document storage + SQLite for ID-hash mapping

## Prerequisites

- Python 3.9+
- Docker & Docker Compose (optional, for containerized deployment)
- S3-compatible storage account (AWS S3, Exoscale, etc.)
- Modern web browser

## Installation

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Antalyse/secure-document-access.git
   cd secure-document-access
   ```

2. **Create a Python virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** (see Configuration section below)

5. **Run the application**:
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

### Docker Setup

1. **Configure environment**:
   ```bash
   cp docker-compose.yml.template docker-compose.yml
   # Edit docker-compose.yml with your S3 credentials
   ```

2. **Build and run**:
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application**:
   Open `http://localhost:5000` in your browser

## Configuration

All configuration is managed through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT` | `https://sos-at-vie-1.exo.io` | S3-compatible endpoint URL |
| `S3_ACCESS_KEY` | `your-access-key` | S3 access key ID |
| `S3_SECRET_KEY` | `your-secret-key` | S3 secret access key |
| `S3_BUCKET` | `your-bucket-name` | S3 bucket name for storing documents |
| `S3_REGION` | `at-vie-1` | S3 region |
| `ENABLE_CREATION_ENDPOINT` | `False` | Enable/disable the `/api/cryptify` endpoint |
| `REQUIRE_HASH` | `False` | Require hash verification for document retrieval |

### Example Configuration

```bash
export S3_ENDPOINT="https://sos-at-vie-1.exo.io"
export S3_ACCESS_KEY="your-exoscale-key"
export S3_SECRET_KEY="your-exoscale-secret"
export S3_BUCKET="documents-bucket"
export S3_REGION="at-vie-1"
export ENABLE_CREATION_ENDPOINT="true"
export REQUIRE_HASH="false"
```

## API Endpoints

### POST `/api/cryptify`
Generate a document ID and hash for a given text.

**Request**:
```json
{
  "text": "Your document content here"
}
```

**Response**:
```json
{
  "document_id": 1,
  "hash": "abc123def456..."
}
```

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Missing text field
- `403 Forbidden`: Endpoint disabled (when `ENABLE_CREATION_ENDPOINT` is False)

### POST `/retrieve`
Retrieve and download a document from S3.

**Request** (form data):
- `document_id`: The document ID (required)
- `hash_string`: The document hash (required if `REQUIRE_HASH` is True)

**Response**: PDF file download

**Status Codes**:
- `200 OK`: Document downloaded successfully
- `400 Bad Request`: Missing document ID
- `403 Forbidden`: Invalid hash or hash verification required
- `404 Not Found`: Document not found in storage
- `500 Internal Server Error`: S3 error


## Usage Examples

### Creating a Document (if enabled)

**Using cURL**:
```bash
curl -X POST http://localhost:5000/api/cryptify \
  -H "Content-Type: application/json" \
  -d '{"text":"My secret document"}'
```

**Using JavaScript**:
```javascript
fetch('http://localhost:5000/api/cryptify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'My secret document' })
})
.then(r => r.json())
.then(data => {
  console.log('Document ID:', data.document_id);
  console.log('Hash:', data.hash);
});
```

### Retrieving a Document

**Using cURL**:
```bash
curl -X POST http://localhost:5000/retrieve \
  -d "document_id=1&hash_string=abc123..." \
  -o document.pdf
```

**Using the Web Interface**:
1. Navigate to `http://localhost:5000`
2. Enter the document ID
3. (If required) Enter the hash string
4. Click "Retrieve Document"

## Security Considerations

1. **Hash Verification**: Enable `REQUIRE_HASH=true` in production to ensure only those with the hash can access documents
2. **S3 Credentials**: Store credentials securely using environment variables, secrets management, or IAM roles
3. **HTTPS**: Deploy behind a reverse proxy (nginx, Apache) with HTTPS in production
4. **Access Logs**: Monitor S3 access logs for suspicious activity
5. **Document IDs**: Document IDs are sequential and predictable—rely on hash verification for security
6. **Partial Hashes**: Minimum 40-character partial hashes reduce security; use full hashes (64 characters) when possible
7. **Rate Limiting**: Implement rate limiting on the application or reverse proxy
8. **Database Security**: SQLite is suitable for single-server deployments; use persistent volumes in Docker

## Project Structure

```
.
├── app.py                      # Flask application and API
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image definition
├── docker-compose.yml.template # Docker Compose template
├── templates/
│   └── index.html             # Web interface
├── logo.png                   # Application logo
└── README.md                  # This file
```

## Data Persistence

- **Document IDs**: Stored in `data/counter.txt` (sequential counter)
- **ID-Hash Mapping**: Stored in `data/kv_store.db` (SQLite database)
- **Documents**: Stored in S3 bucket as `{document_id}.pdf`

For Docker deployments, mount the `data/` directory as a volume to persist data across container restarts.

## Dependencies

- **Flask** (3.0.0): Web framework
- **boto3** (1.34.0): AWS S3 client library
- **gunicorn** (21.2.0): Production WSGI server

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/Antalyse/secure-document-access).
