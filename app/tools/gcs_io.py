import os
from google.cloud import storage

BUCKET_NAME = os.environ.get("WIKI_BUCKET_NAME", "agentwiki-adk-wiki-sg")


def _get_bucket():
    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def read_wiki_file(filename: str) -> str:
    """Reads a markdown file from the wiki GCS bucket.

    Args:
        filename: The path/name of the blob in GCS (e.g., 'index.md', 'entities/entity1.md').
    """
    try:
        bucket = _get_bucket()
        blob = bucket.blob(filename)
        if not blob.exists():
            return ""
        return blob.download_as_text()
    except Exception as e:
        print(f"Error reading wiki file {filename}: {e}")
        return ""


def write_wiki_file(filename: str, content: str):
    """Writes a markdown file to the wiki GCS bucket.

    Args:
        filename: The path/name of the blob in GCS.
        content: The markdown string to write.
    """
    try:
        bucket = _get_bucket()
        blob = bucket.blob(filename)
        blob.upload_from_string(content, content_type="text/markdown")
    except Exception as e:
        print(f"Error writing wiki file {filename}: {e}")


def list_wiki_files(prefix: str = "") -> list[str]:
    """Lists markdown files in the wiki GCS bucket.

    Args:
        prefix: Optional prefix filter for the GCS blobs (e.g., 'entities/').
    """
    try:
        bucket = _get_bucket()
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs if blob.name.endswith(".md")]
    except Exception as e:
        print(f"Error listing wiki files: {e}")
        return []


def wiki_file_exists(filename: str) -> bool:
    """Checks if a file exists in the wiki GCS bucket."""
    try:
        bucket = _get_bucket()
        blob = bucket.blob(filename)
        return blob.exists()
    except Exception as e:
        print(f"Error checking wiki file existence for {filename}: {e}")
        return False
