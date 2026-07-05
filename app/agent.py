# ruff: noqa
import google.auth
from google import genai
from google.adk.workflow import Workflow, START, node
from google.adk.events.event import Event
from google.adk.agents.context import Context
from google.adk.apps import App
from google.genai import types

from app.agents.librarian_agent import librarian_agent
from app.agents.reviewer_agent import reviewer_agent
from app.agents.schema_manager_agent import schema_manager_agent
from app.agents.synthesizer_agent import synthesizer_agent
from app.config import WIKI_BUCKET_NAME, get_current_date_time, make_model
from app.tools.extractor import extract_content
from app.tools.gcs_io import list_wiki_files, read_wiki_file
from app.tools.health import compute_wiki_health


def _get_client():
    _, project_id = google.auth.default()
    return genai.Client(vertexai=True, project=project_id, location="global")


# 1. Classification Node
@node
def classify_route(ctx: Context, node_input: types.Content) -> Event:
    # Check if there is an inline file in user content
    if node_input and node_input.parts:
        for part in node_input.parts:
            if part.inline_data:
                return Event(route="ingest", output=node_input)

    # Check if there's a text part that specifies a local file path or URL
    query_text = ""
    if node_input and node_input.parts:
        for part in node_input.parts:
            if part.text:
                query_text += part.text + "\n"

    # Use LLM classification
    client = _get_client()
    classification_prompt = f"""Classify the user request into one of the following operations:
- "ingest": The user wants to add, ingest, upload, process, or integrate a file, URL, page, or content into the wiki, or specifies a local file path.
- "schema_management": The user wants to review, merge, or apply schema proposals.
- "lint": The user wants to audit, lint, health-check, or check consistency of the wiki.
- "query": The user is asking a question or searching the wiki.

Return ONLY the classification name: "ingest", "schema_management", "lint", or "query". Do not return any other text.

Request: {query_text}"""

    response = client.models.generate_content(
        model=make_model().model,
        contents=classification_prompt,
    )
    classification = (response.text or "query").strip().lower()

    valid_routes = {"ingest", "schema_management", "lint", "query"}
    if classification not in valid_routes:
        classification = "query"

    return Event(output=node_input, route=classification)


# 2. Extractor Node
@node
def run_extractor(ctx: Context, node_input: types.Content) -> str:
    # Check if there is inline_data
    if node_input and node_input.parts:
        for part in node_input.parts:
            if part.inline_data:

                class FakeUserContent:
                    def __init__(self, parts):
                        self.parts = parts

                class FakeToolContext:
                    def __init__(self, parts):
                        self.user_content = FakeUserContent(parts)

                fake_ctx = FakeToolContext(node_input.parts)
                result = extract_content(tool_context=fake_ctx)
                # Save inline GCS path to state if matched
                import re

                match = re.match(r"^\[File Ingested: (raw_data/.*?)\]", result)
                if match:
                    ctx.state["source_path"] = match.group(1)
                return result

    # Otherwise, extract the source path or URL
    query_text = ""
    for part in node_input.parts:
        if part.text:
            query_text += part.text + "\n"

    client = _get_client()
    parse_prompt = f"""Extract the file path or URL to be ingested from the user request. Return ONLY the file path or URL, or "NONE" if none is specified.
    
Request: {query_text}"""
    response = client.models.generate_content(
        model=make_model().model,
        contents=parse_prompt,
    )
    source = (response.text or "NONE").strip().replace('"', "").replace("'", "")
    if source.upper() == "NONE":
        return (
            "Error: No source (URL or file path) provided, and no uploaded file found."
        )

    # If it is a local file, the GCS path will be raw_data/{basename}
    if not (source.startswith("http://") or source.startswith("https://")):
        import os
        from app.tools.extractor import sanitize_filename

        filename = os.path.basename(source)
        filename = sanitize_filename(filename)
        ctx.state["source_path"] = f"raw_data/{filename}"
    else:
        ctx.state["source_path"] = source

    return extract_content(source=source)


# 3. Synthesizer Node
@node(rerun_on_resume=True)
async def run_synthesizer(ctx: Context, node_input: str) -> Event:
    source_path = ctx.state.get("source_path")
    import re

    clean_text = node_input
    match = re.match(r"^\[File Ingested: raw_data/.*?\]\n\n([\s\S]*)", node_input)
    if match:
        clean_text = match.group(1)

    prompt = f"Source Path: {source_path}\nExtracted Content:\n{clean_text}"
    manifest = await ctx.run_node(synthesizer_agent, node_input=prompt)
    return Event(output=manifest, state={"manifest": manifest})


# 4. Reviewer Node
@node(rerun_on_resume=True)
async def run_reviewer(ctx: Context, node_input: str) -> Event:
    prompt = f"Please review the following file manifest:\n{node_input}"
    review_report = await ctx.run_node(reviewer_agent, node_input=prompt)
    return Event(output=review_report, state={"review_report": review_report})


# 5. Librarian Node
@node(rerun_on_resume=True)
async def run_librarian(ctx: Context, node_input: str) -> Event:
    manifest = ctx.state.get("manifest")
    source_path = ctx.state.get("source_path") or "uploaded file"

    prompt = f"""Summarize and log the ingestion:
Source: {source_path}
Synthesizer Manifest:
{manifest}
Reviewer Report:
{node_input}"""

    lib_output = await ctx.run_node(librarian_agent, node_input=prompt)

    response_msg = f"""### Ingestion Complete
- **Source**: `{source_path}`
- **Pages updated/created**:
{manifest}

### Review Report
{node_input}

### Wiki Index status
{lib_output}"""

    yield Event(
        content=types.Content(
            role="model", parts=[types.Part.from_text(text=response_msg)]
        )
    )
    yield Event(output=response_msg)


# 6. Query Node (with Programmatic Grounding Context)
@node
async def run_query(ctx: Context, node_input: types.Content) -> Event:
    query_text = ""
    for part in node_input.parts:
        if part.text:
            query_text += part.text + "\n"

    # Step 1: Read index.md and log.md
    index_content = read_wiki_file("index.md")
    log_content = read_wiki_file("log.md")

    # Step 2: Use LLM to identify relevant page filenames from index.md and log.md
    client = _get_client()
    search_prompt = f"""You are a search assistant. Given the wiki index, update log, and a user query, identify all relevant page filenames (.md files) that may contain the answer. Return them as a comma-separated list of filenames, e.g. "sources/pra_ss4_24.md, entities/capital_buffers.md". Return only the list of filenames, or "NONE" if no pages are relevant.
    
Wiki Index:
{index_content}

Update Log (log.md):
{log_content}

User Query: {query_text}"""

    response = client.models.generate_content(
        model=make_model().model,
        contents=search_prompt,
    )
    search_results = response.text or ""

    filenames = []
    if "NONE" not in search_results.upper():
        filenames = [
            f.strip() for f in search_results.split(",") if f.strip().endswith(".md")
        ]

    grounding_context = []
    for fname in filenames:
        content = read_wiki_file(fname)
        if content:
            grounding_context.append(f"=== Page: {fname} ===\n{content}")

            # Step 3: Find referenced source files in page content/frontmatter
            import re

            sources_matches = re.findall(r"sources:\s*\[(.*?)\]", content)
            for sm in sources_matches:
                s_files = [
                    sf.strip().replace("'", "").replace('"', "")
                    for sf in sm.split(",")
                    if sf.strip()
                ]
                for sf in s_files:
                    s_content = read_wiki_file(sf)
                    if s_content:
                        grounding_context.append(
                            f"=== Source Summary: {sf} ===\n{s_content}"
                        )
                        # Step 4: Check if source summary contains a link to raw_data/
                        raw_link_match = re.search(
                            r"\[Original File\]\(\.\./(raw_data/.*?)\)", s_content
                        )
                        if raw_link_match:
                            raw_path = raw_link_match.group(1)
                            raw_content = read_wiki_file(raw_path)
                            if raw_content:
                                grounding_context.append(
                                    f"=== Original Raw File: {raw_path} ===\n{raw_content}"
                                )

            # Also check for inline links to sources/
            inline_matches = re.findall(r"\]\(\.\./(sources/.*?\.md)\)", content)
            for im in inline_matches:
                s_content = read_wiki_file(im)
                if s_content:
                    grounding_context.append(
                        f"=== Source Summary: {im} ===\n{s_content}"
                    )
                    raw_link_match = re.search(
                        r"\[Original File\]\(\.\./(raw_data/.*?)\)", s_content
                    )
                    if raw_link_match:
                        raw_path = raw_link_match.group(1)
                        raw_content = read_wiki_file(raw_path)
                        if raw_content:
                            grounding_context.append(
                                f"=== Original Raw File: {raw_path} ===\n{raw_content}"
                            )

    # Add index and log to grounding context explicitly
    grounding_context.append(f"=== Wiki Index (index.md) ===\n{index_content}")
    grounding_context.append(f"=== Update Log (log.md) ===\n{log_content}")

    # Step 5: Generate cited grounded answer
    context_str = "\n\n".join(grounding_context)
    final_prompt = f"""You are the Antigravity Wiki Agent. Answer the user query using the provided grounding context from the wiki (which includes index files, logs, source summaries, and original raw documents).
    
Chronology & Temporal Logic:
- Refer to `log.md` and page timestamps to understand when data was ingested and updated.
- If there are conflicting claims, contradictions, or updates, the entry with the most recent timestamp in `log.md` or page frontmatter represents the current active state of the wiki.

Requirements:
- Your response must be highly thorough, detailed, and formatted in clear markdown.
- You MUST explicitly cite all wiki pages, source summaries, and original raw GCS files (e.g. `raw_data/filename`) you used to construct your answer.
- If the context doesn't contain the answer, state that you don't know based on the wiki.

Grounding Context:
{context_str}

User Query: {query_text}"""

    response_stream = client.models.generate_content_stream(
        model=make_model().model,
        contents=final_prompt,
    )

    answer_text = ""
    for chunk in response_stream:
        if chunk.text:
            answer_text += chunk.text
            yield Event(
                content=types.Content(
                    role="model", parts=[types.Part.from_text(text=chunk.text)]
                )
            )

    yield Event(output=answer_text)


# 7. Schema Manager Node
@node(rerun_on_resume=True)
async def run_schema_manager(ctx: Context, node_input: types.Content) -> Event:
    async for event in schema_manager_agent.run_async(ctx.get_invocation_context()):
        yield event


# 8. Linter/Audit Node
@node(rerun_on_resume=True)
async def run_linter(ctx: Context, node_input: types.Content) -> Event:
    health_result = compute_wiki_health()
    all_files = list_wiki_files()
    manifest_str = "\n".join([f"UPDATE {f}" for f in all_files])
    prompt = (
        f"Please perform a full wiki consistency check on these files:\n{manifest_str}"
    )

    review_report = await ctx.run_node(reviewer_agent, node_input=prompt)

    response_msg = f"""### Wiki Health & Audit Report
- **Health Score**: {health_result}

### Audit Report
{review_report}"""

    yield Event(
        content=types.Content(
            role="model", parts=[types.Part.from_text(text=response_msg)]
        )
    )
    yield Event(output=response_msg)


root_agent = Workflow(
    name="wiki_orchestrator",
    edges=[
        (START, classify_route),
        (
            classify_route,
            {
                "ingest": run_extractor,
                "query": run_query,
                "schema_management": run_schema_manager,
                "lint": run_linter,
            },
        ),
        (run_extractor, run_synthesizer),
        (run_synthesizer, run_reviewer),
        (run_reviewer, run_librarian),
    ],
    sub_agents=[
        synthesizer_agent,
        reviewer_agent,
        librarian_agent,
        schema_manager_agent,
    ],
    description="Wiki Orchestrator Workflow Agent",
)

app = App(
    root_agent=root_agent,
    name="app",
)
