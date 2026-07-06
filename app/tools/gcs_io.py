import mimetypes

from google.cloud import storage

from app.config import WIKI_BUCKET_NAME

BUCKET_NAME = WIKI_BUCKET_NAME


def _get_bucket():
    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def read_wiki_file(filename: str) -> str:
    """Reads a file from the wiki GCS bucket. Supports markdown and PDF content extraction.

    Args:
        filename: The path/name of the blob in GCS (e.g., 'index.md', 'entities/entity1.md').
    """
    try:
        bucket = _get_bucket()
        blob = bucket.blob(filename)
        if not blob.exists():
            return ""

        if filename.lower().endswith(".pdf"):
            import google.auth
            from google import genai
            from google.genai import types

            pdf_bytes = blob.download_as_bytes()
            _, project_id = google.auth.default()
            client = genai.Client(vertexai=True, project=project_id, location="global")

            pdf_part = types.Part.from_bytes(
                data=pdf_bytes, mime_type="application/pdf"
            )
            prompt = "Please provide a detailed, comprehensive markdown transcription of this document. Extract all core information, tables, and concepts."

            response = client.models.generate_content(
                model="gemini-3.5-flash", contents=[pdf_part, prompt]
            )
            return response.text or ""

        return blob.download_as_text()
    except Exception as e:
        print(f"Error reading wiki file {filename}: {e}")
        return ""


def upload_file_to_gcs(local_path: str, gcs_path: str) -> None:
    """Uploads a local file to the wiki GCS bucket.

    Args:
        local_path: The local filesystem path.
        gcs_path: The path/name of the blob in GCS (e.g., 'raw_data/my_file.pdf').
    """
    try:
        bucket = _get_bucket()
        blob = bucket.blob(gcs_path)
        content_type, _ = mimetypes.guess_type(local_path)
        blob.upload_from_filename(local_path, content_type=content_type)
    except Exception as e:
        print(f"Error uploading file {local_path} to {gcs_path}: {e}")
        raise e


def upload_bytes_to_gcs(data: bytes, gcs_path: str, content_type: str) -> None:
    """Uploads raw bytes to the wiki GCS bucket.

    Args:
        data: The raw bytes.
        gcs_path: The path/name of the blob in GCS (e.g., 'raw_data/my_file.pdf').
        content_type: The content type string of the blob.
    """
    try:
        bucket = _get_bucket()
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(data, content_type=content_type)
    except Exception as e:
        print(f"Error uploading bytes to {gcs_path}: {e}")
        raise e


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
