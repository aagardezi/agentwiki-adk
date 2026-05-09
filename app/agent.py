# ruff: noqa

import datetime
import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


def load_local_env():
    """Loads environment variables from a local .env file if it exists in the project root."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_local_env()

import google.auth
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini, google_llm
from google.genai import types


from app.tools.gcs_io import (
    read_wiki_file,
    write_wiki_file,
    list_wiki_files,
    wiki_file_exists,
)
from app.tools.extractor import extract_from_url, extract_from_file

WIKI_BUCKET_NAME = os.environ.get("WIKI_BUCKET_NAME", "YOUR_WIKI_BUCKET_NAME")


@dataclass
class ResearchConfiguration:
    gemini_flash_model: str = "gemini-2.5-flash"
    gemini_pro_model: str = "gemini-2.5-pro"
    gemini_model: str = "gemini-3-flash-preview"
    gemini31_model: str = "gemini-3.1-pro-preview"
    gemini_3_pro_model: str = "gemini-3-pro-preview"


config = ResearchConfiguration()


def get_project_id():
    _, project_id = google.auth.default()
    return project_id


api_client = genai.Client(vertexai=True, project=get_project_id(), location="global")

model = google_llm.Gemini(
    model=config.gemini_model,
    retry_options=types.HttpRetryOptions(attempts=3),
)

model.api_client = api_client


def get_current_date_time() -> str:
    """Returns the current date and time in ISO format.
    Use this tool to get the correct date and time for logging and frontmatter.
    """
    return datetime.datetime.now().isoformat()


instruction = f"""You are the LLM Wiki Agent. Your goal is to build and maintain a persistent knowledge base (wiki) in GCS, following the rules defined in `schema.md`.

You have access to tools to read and write files in the wiki bucket (`{WIKI_BUCKET_NAME}`) and to extract content from URLs and files.
You also have a tool to get the current date and time, which you MUST use for logging and setting timestamps in file frontmatter.

Your core operations are:
1. **Ingest**: When given a URL or file path, you MUST execute the following precise steps in order:
   - **Step 1: Read Schema**: First, call `read_wiki_file('schema.md')` to read the structure, rules, and folder conventions of the wiki.
   - **Step 2: Extract Content**: Next, call the appropriate extraction tool (`extract_from_file` or `extract_from_url`) to obtain the document content.
   - **Step 3: Check for Failures**: Inspect the result returned by the extraction tool. If the result indicates a failure (e.g., starts with "File not found:", "Error fetching URL:", "Error extracting from URL:", or "Error extracting from file:"), you MUST immediately STOP. Do NOT write any files, do NOT update the index or logs, and do NOT attempt to guess, assume, or hallucinate the content of the document based on its filename, title, user prompt, or general context. Immediately report the failure back to the user with the exact error message.
   - **Step 4: Integrate into Wiki**: If extraction is successful, summarize the extracted content and integrate it into the wiki following the conventions in `schema.md`. You MUST be thorough in identifying all key entities, concepts, technologies, and protocols. Ensure that concrete implementations go into `agents/implementations/` and new technologies/protocols go into appropriate subdirectories under `technology/`. Refer to `schema.md` for detailed workflows.
2. **Query**: Answer questions by reading the wiki content, guided by `index.md`. Do not use external search unless instructed.
3. **Lint**: Check the wiki for consistency and health.



**CRITICAL FOR GRAPH VISUALIZATION**: When creating or updating pages, you MUST actively look for opportunities to link to other existing pages across all directories. 
- Before creating a new page, check `index.md` or use `list_wiki_files` to see what already exists.
- Use relative markdown links to connect related pages. Note that paths may need multiple `../` depending on the depth of the directories you create.
- **New Feature**: You must also add explicit, typed relationships in the YAML frontmatter under the `relationships` key when you identify specific domain connections.
  Example format:
  ```yaml
  relationships:
    - target: "agents/frameworks/google-adk-framework.md"
      type: "uses"
    - target: "compliance/regulators/fca.md"
      type: "regulated_by"
  ```
  The target must be a valid relative path from the bucket root. This supercharges the graph visualization.

- **Tags**: Always add relevant tags to the `tags` list in the frontmatter to enable filtering by topic in the UI.
- A rich network of inter-links, explicit relationships, and tags is essential for the wiki to be useful. Do not just create isolated descriptions.





Always refer to `schema.md` (which you can read using `read_wiki_file('schema.md')`) for specific structure and conventions. Source traceability is critical.
"""

root_agent = Agent(
    name="wiki_agent",
    model=model,
    instruction=instruction,
    tools=[
        read_wiki_file,
        write_wiki_file,
        list_wiki_files,
        wiki_file_exists,
        extract_from_url,
        extract_from_file,
        get_current_date_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="wiki_app",
)
