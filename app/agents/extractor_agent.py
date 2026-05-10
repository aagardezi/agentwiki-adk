from google.adk.agents import Agent

from app.config import get_current_date_time, make_model
from app.tools.extractor import extract_from_file, extract_from_url

extractor_agent = Agent(
    name="extractor_agent",
    model=make_model(),
    description="Fetches and extracts raw content from URLs, local files, or conversation context. Returns the full extracted text with source metadata.",
    instruction="""You are the Extractor Agent. Your sole responsibility is to obtain and return the complete raw content of a source document.

You will be given one of:
- A URL to fetch and extract
- A local file path to read
- A notification that the document content is already present in the conversation

Steps:
1. If the document content is already in the conversation history (e.g. the user uploaded a file or PDF), return it directly — do NOT call any extraction tool.
2. If given a URL, call `extract_from_url`.
3. If given a file path, call `extract_from_file`.
4. If extraction fails (result starts with "Error", "File not found:", etc.), return the exact error string — do not fabricate or guess content.
5. Return the full extracted content without summarizing or truncating. Include all text, tables, and structured information.

You do NOT write to the wiki. Your output is passed to the Synthesizer Agent.
""",
    tools=[extract_from_url, extract_from_file, get_current_date_time],
)
