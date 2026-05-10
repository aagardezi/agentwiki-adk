# ruff: noqa
import datetime
import os

import google.auth
from google import genai
from google.adk.models import google_llm
from google.genai import types


def load_local_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_local_env()

WIKI_BUCKET_NAME = os.environ.get("WIKI_BUCKET_NAME")
if not WIKI_BUCKET_NAME:
    raise RuntimeError(
        "WIKI_BUCKET_NAME environment variable is not set. "
        "Add it to your .env file or environment before starting the agent."
    )


def _get_project_id() -> str:
    _, project_id = google.auth.default()
    return project_id


def make_model(model_name: str = "gemini-3-flash-preview") -> google_llm.Gemini:
    """Creates a configured Gemini model instance with Vertex AI client."""
    api_client = genai.Client(
        vertexai=True, project=_get_project_id(), location="global"
    )
    model = google_llm.Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
    )
    model.api_client = api_client
    return model


def get_current_date_time() -> str:
    """Returns the current date and time in ISO format.
    Use this tool to get the correct date and time for logging and frontmatter.
    """
    return datetime.datetime.now().isoformat()
