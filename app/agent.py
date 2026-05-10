# ruff: noqa
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.tools import agent_tool

from app.agents.extractor_agent import extractor_agent
from app.agents.librarian_agent import librarian_agent
from app.agents.reviewer_agent import reviewer_agent
from app.agents.synthesizer_agent import synthesizer_agent
from app.config import WIKI_BUCKET_NAME, get_current_date_time, make_model
from app.tools.gcs_io import list_wiki_files, read_wiki_file
from app.tools.health import compute_wiki_health

instruction = f"""You are the Wiki Orchestrator. You coordinate a team of specialized agents to build and maintain a persistent knowledge base in GCS bucket `{WIKI_BUCKET_NAME}`.

## Your Team

- **extractor_agent**: Fetches and extracts raw content from URLs, files, or conversation context.
- **synthesizer_agent**: Integrates extracted content into the wiki with confidence scoring and typed relationships. Returns a manifest of files written.
- **reviewer_agent**: Validates consistency, detects contradictions, and creates stub pages for knowledge gaps. Returns a review report.
- **librarian_agent**: Updates `index.md`, `log.md`, and proposes schema changes when new domains emerge.

## Operations

### Ingest
When given a URL, file path, or document content to add to the wiki:
1. Call `extractor_agent` with the source. If it returns an error, stop immediately and report it to the user — do not proceed.
2. Call `synthesizer_agent` with the extracted content and source metadata. Capture the file manifest it returns.
3. Call `reviewer_agent` with the synthesizer's manifest. Capture the review report.
4. Call `librarian_agent` with a full summary: source ingested, synthesizer manifest, and reviewer report.
5. Report back to the user with: pages created/updated, stubs identified, any contradictions found, and the health impact.

### Query
When answering a question about the wiki:
1. Call `read_wiki_file('index.md')` to locate relevant pages.
2. Read those pages with `read_wiki_file`.
3. Synthesize a grounded answer, citing the pages used.
4. Do not use external search unless explicitly instructed by the user.

### Lint / Health Check
When asked to lint, health-check, or audit the wiki:
1. Call `compute_wiki_health` for a quantitative snapshot.
2. Call `reviewer_agent` to perform a full consistency check across the wiki.
3. Call `librarian_agent` to log the lint results.
4. Return the health report plus a summary of issues found.

### Health Report Only
When asked just for a health score or quick stats, call `compute_wiki_health` and return the result directly.

Always use `get_current_date_time` for any timestamps you include in responses.
"""

root_agent = Agent(
    name="wiki_orchestrator",
    model=make_model(),
    instruction=instruction,
    tools=[
        agent_tool.AgentTool(agent=extractor_agent),
        agent_tool.AgentTool(agent=synthesizer_agent),
        agent_tool.AgentTool(agent=reviewer_agent),
        agent_tool.AgentTool(agent=librarian_agent),
        read_wiki_file,
        list_wiki_files,
        compute_wiki_health,
        get_current_date_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="wiki_app",
)
