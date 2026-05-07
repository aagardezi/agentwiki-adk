# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools.gcs_io import (
    read_wiki_file,
    write_wiki_file,
    list_wiki_files,
    wiki_file_exists,
)
from app.tools.extractor import extract_from_url, extract_from_file

WIKI_BUCKET_NAME = os.environ.get("WIKI_BUCKET_NAME", "agentwiki-adk-wiki-sg")

def get_current_date_time() -> str:
    """Returns the current date and time in ISO format.
    Use this tool to get the correct date and time for logging and frontmatter.
    """
    return datetime.datetime.now().isoformat()

instruction = f"""You are the LLM Wiki Agent. Your goal is to build and maintain a persistent knowledge base (wiki) in GCS, following the rules defined in `schema.md`.

You have access to tools to read and write files in the wiki bucket (`{WIKI_BUCKET_NAME}`) and to extract content from URLs and files.
You also have a tool to get the current date and time, which you MUST use for logging and setting timestamps in file frontmatter.

Your core operations are:
1. **Ingest**: When given a URL or file path, extract the content, summarize it, and integrate it into the wiki (updating index, entities, concepts, and log).
2. **Query**: Answer questions by reading the wiki content, guided by `index.md`. Do not use external search unless instructed.
3. **Lint**: Check the wiki for consistency and health.

Always refer to `schema.md` (which you can read using `read_wiki_file('schema.md')`) for specific structure and conventions. Source traceability is critical.
"""

root_agent = Agent(
    name="wiki_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
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
