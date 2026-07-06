# ruff: noqa
import asyncio
from typing import Any
import google.auth
from google import genai
from google.adk.workflow import Workflow, START, node
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.agents.context import Context
from google.adk.apps import App
from google.genai import types

from app.agents.librarian_agent import librarian_agent
from app.agents.reviewer_agent import reviewer_agent
from app.agents.schema_manager_agent import schema_manager_agent
from app.agents.synthesizer_agent import synthesizer_agent
from app.agents.wiki_researcher_agent import wiki_researcher_agent
from app.agents.critic_agent import critic_agent
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
    # Reset critic loop state for any new incoming query
    ctx.state["validation_loops"] = 0
    ctx.state["critic_feedback"] = None
    ctx.state["draft_response"] = None
    ctx.state["original_input"] = None
    ctx.state["original_query"] = None

    # Check if there is an inline file in user content
    if node_input and node_input.parts:
        for part in node_input.parts or []:
            if part.inline_data:
                return Event(actions=EventActions(route="ingest"), output=node_input)

    # Check if there's a text part that specifies a local file path or URL
    query_text = ""
    if node_input and node_input.parts:
        for part in node_input.parts or []:
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

    return Event(output=node_input, actions=EventActions(route=classification))


# 2. Extractor Node
@node
def run_extractor(ctx: Context, node_input: types.Content) -> str:
    # Check if there is inline_data
    if node_input and node_input.parts:
        for part in node_input.parts or []:
            if part.inline_data:

                class FakeUserContent:
                    def __init__(self, parts):
                        self.parts = parts

                class FakeToolContext:
                    def __init__(self, parts):
                        self.user_content = FakeUserContent(parts)

                fake_ctx = FakeToolContext(node_input.parts)
                result = extract_content(tool_context=fake_ctx)
                import re

                match = re.match(r"^\[File Ingested: (raw_data/.*?)\]", result)
                if match:
                    ctx.state["source_path"] = match.group(1)
                return result

    # Otherwise, extract the source path or URL
    query_text = ""
    for part in node_input.parts or []:
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
    return Event(
        output=manifest, actions=EventActions(state_delta={"manifest": manifest})
    )


# 4. Reviewer Node
@node(rerun_on_resume=True)
async def run_reviewer(ctx: Context, node_input: str) -> Event:
    prompt = f"Please review the following file manifest:\n{node_input}"
    review_report = await ctx.run_node(reviewer_agent, node_input=prompt)
    return Event(
        output=review_report,
        actions=EventActions(state_delta={"review_report": review_report}),
    )


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


# 6. Query Node (using wiki_researcher_agent with Critic loop support)
@node(rerun_on_resume=True)
async def run_query(ctx: Context, node_input: Any) -> Event:
    # Extract and save original user query text on the first run of this query path
    original_query = ctx.state.get("original_query")
    if not original_query:
        query_text = ""
        if node_input and hasattr(node_input, "parts") and node_input.parts:
            for part in node_input.parts or []:
                if part.text:
                    query_text += part.text + "\n"
        ctx.state["original_query"] = query_text

    draft_response = ""
    feedback = ctx.state.get("critic_feedback")
    prev_draft = ctx.state.get("draft_response")

    if feedback and prev_draft:
        # We are in a revision loop! Feed the previous draft and feedback into prompt.
        query_text = ctx.state.get("original_query", "")

        revised_prompt = f"""The previous draft response was rejected by the critic. Please revise the response based on the feedback.

Previous Draft:
{prev_draft}

Critic's Feedback:
{feedback}

Original User Query:
{query_text}"""
        revised_content = types.Content(
            role="user", parts=[types.Part.from_text(text=revised_prompt)]
        )
        user_event = Event(author="user", content=revised_content)
        if user_event.content is not None:
            user_event.content.role = "user"
        yield user_event

        # Yield to let the runner process and append user_event to the session
        await asyncio.sleep(0)

        async for event in wiki_researcher_agent.run_async(
            ctx.get_invocation_context()
        ):
            if event.content and event.content.parts:
                for part in event.content.parts or []:
                    if part.text:
                        draft_response += part.text
            yield event
    else:
        # Standard initial run
        async for event in wiki_researcher_agent.run_async(
            ctx.get_invocation_context()
        ):
            if event.content and event.content.parts:
                for part in event.content.parts or []:
                    if part.text:
                        draft_response += part.text
            yield event

    ctx.state["draft_response"] = draft_response
    yield Event(output=draft_response)


# 7. Critic Node
@node(rerun_on_resume=True)
async def run_critic(ctx: Context, node_input: str) -> Event:
    loop_count = ctx.state.get("validation_loops", 0)
    draft_response = ctx.state.get("draft_response", "")

    # Cap validation loop at a maximum of 2 iterations (forcing approval on the 3rd iteration)
    if loop_count >= 2:
        yield Event(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="\n\n*Critic validation threshold reached. Response auto-approved.*"
                    )
                ],
            )
        )
        yield Event(actions=EventActions(route="approved"), output=draft_response)
        return

    original_query = ctx.state.get("original_query", "")
    critic_prompt = f"""Original User Query: {original_query}

Draft Response to Evaluate:
{draft_response}
"""
    critic_output = await ctx.run_node(critic_agent, node_input=critic_prompt)

    import re

    status_match = re.search(
        r"STATUS:\s*(APPROVED|REVISE)", critic_output, re.IGNORECASE
    )
    status = "APPROVED"
    feedback = ""

    if status_match:
        status = status_match.group(1).upper()

    if status == "REVISE":
        feedback_match = re.search(
            r"Feedback:\s*([\s\S]*)", critic_output, re.IGNORECASE
        )
        if feedback_match:
            feedback = feedback_match.group(1).strip()
        else:
            feedback = critic_output.replace(status_match.group(0), "").strip()

    if status == "APPROVED":
        from google.adk.events.event import NodeInfo

        yield Event(
            actions=EventActions(route="approved"),
            content=types.Content(
                role="model", parts=[types.Part.from_text(text=draft_response)]
            ),
            node_info=NodeInfo(message_as_output=True),
        )
    else:
        ctx.state["validation_loops"] = loop_count + 1
        ctx.state["critic_feedback"] = feedback

        # Notify the user about revision in progress
        yield Event(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=f"\n*Critic requested revision (Loop {loop_count + 1}/2). Feedback:* {feedback}\n*Re-evaluating and refining response...*\n"
                    )
                ],
            )
        )
        yield Event(actions=EventActions(route="revise"))


# 8. Schema Manager Node
@node(rerun_on_resume=True)
async def run_schema_manager(ctx: Context, node_input: types.Content) -> Event:
    async for event in schema_manager_agent.run_async(ctx.get_invocation_context()):
        yield event


# 9. Linter/Audit Node
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
        (run_query, run_critic),
        (
            run_critic,
            {
                "revise": run_query,
            },
        ),
    ],
    description="Wiki Orchestrator Workflow Agent with Verification & Critic Loop",
)

app = App(
    root_agent=root_agent,
    name="app",
)
