from typing import AsyncGenerator

from google.adk.agents import Agent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from typing_extensions import override

from app.config import WIKI_BUCKET_NAME, get_current_date_time, make_model
from app.tools.gcs_io import read_wiki_file, write_wiki_file

_schema_merge_agent = Agent(
    name="schema_merge_agent",
    model=make_model(),
    description="Merges approved schema proposals from schema_proposals.md into schema.md.",
    instruction=f"""You are the Schema Merge Agent. You manage schema evolution for the wiki at `{WIKI_BUCKET_NAME}`.

You are called when there are pending proposals in `schema_proposals.md`. Your tasks:

**Step 1 — Read and present proposals**
1. Call `read_wiki_file('schema_proposals.md')` to get all pending proposals.
2. Call `read_wiki_file('schema.md')` to understand the current schema.
3. Present each proposal clearly to the user, numbered, showing:
   - The new directory path
   - The reason it was created
   - Sample pages
   - The suggested schema.md addition
4. Ask the user: "Which proposals would you like to merge? Reply with the numbers (e.g. '1, 3'), 'all', or 'none'."

**Step 2 — Wait for user response, then merge approved proposals**
Once the user replies:
1. Add the approved directory entries into `schema.md` under the Directory Structure section.
2. Rewrite `schema.md` with the additions included.
3. Remove the approved proposals from `schema_proposals.md`, keeping any unapproved ones.
4. Write the updated `schema_proposals.md` back (write an empty file if all were approved).

**Step 3 — Confirm**
Report which proposals were merged and confirm that `schema.md` has been updated.
""",
    tools=[read_wiki_file, write_wiki_file, get_current_date_time],
)


class SchemaManagerAgent(BaseAgent):
    """Conditionally runs schema merge only when pending proposals exist in GCS."""

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        proposals = read_wiki_file("schema_proposals.md")

        if not proposals or not proposals.strip():
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text="No pending schema proposals found in `schema_proposals.md`. Nothing to merge."
                        )
                    ],
                ),
            )
            return

        async with Aclosing(_schema_merge_agent.run_async(ctx)) as agen:
            async for event in agen:
                yield event


schema_manager_agent = SchemaManagerAgent(
    name="schema_manager_agent",
    description="Checks for pending schema proposals and, if found, presents them to the user and merges approved ones into schema.md.",
    sub_agents=[_schema_merge_agent],
)
