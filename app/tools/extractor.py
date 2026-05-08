import os

import google.auth
import requests
from google import genai
from google.genai import types


def _get_client():
    _, project_id = google.auth.default()
    return genai.Client(vertexai=True, project=project_id, location="global")


def extract_from_url(url: str) -> str:
    """Extracts core text from a URL using Gemini."""
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return f"Error fetching URL: {resp.status_code}"

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
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
        client = _get_client()

        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            pdf_part = types.Part.from_bytes(
                data=pdf_bytes, mime_type="application/pdf"
            )
            prompt = "Please provide a detailed, comprehensive markdown transcription of this document. Extract all core information, tables, and concepts."

            response = client.models.generate_content(
                model="gemini-3-flash-preview", contents=[pdf_part, prompt]
            )

            return response.text
        else:
            # Assume text file
            with open(file_path) as f:
                content = f.read()
            return content

    except Exception as e:
        return f"Error extracting from file: {e}"
