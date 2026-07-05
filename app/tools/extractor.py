import os

import google.auth
import requests
from google import genai
from google.adk.tools import ToolContext
from google.genai import types


def _get_client():
    _, project_id = google.auth.default()
    return genai.Client(vertexai=True, project=project_id, location="global")


def sanitize_filename(name: str) -> str:
    """Sanitizes filename by replacing spaces with underscores and removing special characters."""
    import re

    # Replace spaces and consecutive whitespace with a single underscore
    clean_name = re.sub(r"\s+", "_", name)
    # Retain only word characters, dots, hyphens, and underscores
    clean_name = re.sub(r"[^\w\.\-]", "", clean_name)
    return clean_name


def extract_from_url(url: str) -> str:
    """Extracts core text from a URL using Gemini."""
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return f"Error fetching URL: {resp.status_code}"

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"Extract the core text and documentation from this webpage:\n{resp.text}",
        )

        return response.text
    except Exception as e:
        return f"Error extracting from URL: {e}"


def extract_from_file(file_path: str) -> str:
    """Extracts content from a file (supports text and PDF)."""
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    try:
        from app.tools.gcs_io import upload_file_to_gcs

        filename = os.path.basename(file_path)
        filename = sanitize_filename(filename)
        upload_file_to_gcs(file_path, f"raw_data/{filename}")
    except Exception as e:
        return f"Error copying raw file to GCS: {e}"

    try:
        client = _get_client()

        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            pdf_part = types.Part.from_bytes(
                data=pdf_bytes, mime_type="application/pdf"
            )
            prompt = "Please provide a detailed, comprehensive markdown transcription of this document. Extract all core information, tables, and concepts."

            response = client.models.generate_content(
                model="gemini-3.5-flash", contents=[pdf_part, prompt]
            )

            return response.text
        else:
            # Assume text file
            with open(file_path) as f:
                content = f.read()
            return content

    except Exception as e:
        return f"Error extracting from file: {e}"


def extract_content(
    source: str | None = None,
    tool_context: ToolContext | None = None,
) -> str:
    """Extracts raw content from a URL, a local file path, or the uploaded file in conversation history.

    If the user has uploaded a file directly to the conversation, that file will
    be extracted automatically. Otherwise, extracts from the provided URL or file path.

    Args:
        source: Optional URL or file path.
        tool_context: Injected ADK ToolContext.
    """
    # 1. Check if there's an uploaded file in user_content
    if tool_context and tool_context.user_content and tool_context.user_content.parts:
        for part in tool_context.user_content.parts:
            if part.inline_data:
                try:
                    import mimetypes

                    from app.config import get_current_date_time
                    from app.tools.gcs_io import upload_bytes_to_gcs

                    filename = part.inline_data.display_name
                    mime_type = part.inline_data.mime_type

                    if filename:
                        filename = sanitize_filename(filename)
                    else:
                        ext = mimetypes.guess_extension(mime_type) or ".bin"
                        safe_time = get_current_date_time().replace(":", "-")
                        filename = f"uploaded_file_{safe_time}{ext}"

                    upload_bytes_to_gcs(
                        part.inline_data.data,
                        f"raw_data/{filename}",
                        content_type=mime_type,
                    )
                except Exception as e:
                    return f"Error copying uploaded raw file to GCS: {e}"

                try:
                    client = _get_client()
                    prompt = "Please provide a detailed, comprehensive markdown transcription of this document. Extract all core information, tables, and concepts."
                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=[part, prompt],
                    )
                    transcription = response.text or ""
                    return f"[File Ingested: raw_data/{filename}]\n\n{transcription}"
                except Exception as e:
                    return f"Error extracting from uploaded file: {e}"

    # 2. Fall back to url or local file path
    if not source:
        return (
            "Error: No source (URL or file path) provided, and no uploaded file found."
        )

    if source.startswith("http://") or source.startswith("https://"):
        return extract_from_url(source)
    else:
        return extract_from_file(source)
