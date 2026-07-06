# Copyright 2026 Google LLC
from unittest.mock import patch

import pytest
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_load_skills():
    from app.agents.critic_agent import critic_agent
    from app.agents.wiki_researcher_agent import wiki_researcher_agent

    try:
        from google.adk.tools import SkillToolset
    except ImportError:
        from google.adk.tools.skill_toolset import SkillToolset

    researcher_skill_toolsets = [
        t for t in wiki_researcher_agent.tools if isinstance(t, SkillToolset)
    ]
    critic_skill_toolsets = [
        t for t in critic_agent.tools if isinstance(t, SkillToolset)
    ]

    assert len(researcher_skill_toolsets) == 1
    assert len(critic_skill_toolsets) == 1

    skills_names = [s.name for s in researcher_skill_toolsets[0].skills]
    assert "wiki-traversal" in skills_names
    assert "report-writing" in skills_names


@pytest.mark.asyncio
async def test_critic_loop_revision_and_cap() -> None:
    call_count = 0

    async def mock_critic_run(invocation_context, node_input=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(
                            text="STATUS: REVISE\nFeedback: Please mention the exact path of raw_data file."
                        )
                    ],
                )
            )
        else:
            yield Event(
                content=types.Content(
                    role="model", parts=[types.Part.from_text(text="STATUS: APPROVED")]
                )
            )

    original_run_async = LlmAgent.run_async

    async def mock_run_async(self, *args, **kwargs):
        if self.name == "critic_agent":
            async for event in mock_critic_run(*args, **kwargs):
                yield event
        else:
            async for event in original_run_async(self, *args, **kwargs):
                yield event

    with patch.object(LlmAgent, "run_async", autospec=True, side_effect=mock_run_async):
        session_service = InMemorySessionService()
        session = session_service.create_session_sync(
            user_id="test_user", app_name="test"
        )
        runner = Runner(
            agent=root_agent, session_service=session_service, app_name="test"
        )

        message = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="What is the secret token of the integration test document?"
                )
            ],
        )

        events = list(
            runner.run(
                new_message=message,
                user_id="test_user",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )

        assert call_count == 2, (
            f"Expected critic to be called exactly 2 times, got {call_count}"
        )
        assert len(events) > 0

        session_after = session_service.get_session_sync(
            session_id=session.id, user_id="test_user", app_name="test"
        )
        has_revision_event = False
        for event in session_after.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and "Critic's Feedback:" in part.text:
                        has_revision_event = True
                        break
        assert has_revision_event, (
            "Expected a user revision event in session history containing critic feedback."
        )


@pytest.mark.asyncio
async def test_critic_loop_cap_always_revise() -> None:
    call_count = 0

    async def mock_critic_run_always_revise(invocation_context, node_input=None):
        nonlocal call_count
        call_count += 1
        yield Event(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=f"STATUS: REVISE\nFeedback: Critic rejection number {call_count}. Please revise."
                    )
                ],
            )
        )

    original_run_async = LlmAgent.run_async

    async def mock_run_async(self, *args, **kwargs):
        if self.name == "critic_agent":
            async for event in mock_critic_run_always_revise(*args, **kwargs):
                yield event
        else:
            async for event in original_run_async(self, *args, **kwargs):
                yield event

    with patch.object(LlmAgent, "run_async", autospec=True, side_effect=mock_run_async):
        session_service = InMemorySessionService()
        session = session_service.create_session_sync(
            user_id="test_user", app_name="test"
        )
        runner = Runner(
            agent=root_agent, session_service=session_service, app_name="test"
        )

        message = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="What is the secret token of the integration test document?"
                )
            ],
        )

        events = list(
            runner.run(
                new_message=message,
                user_id="test_user",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )

        assert call_count == 2, (
            f"Expected critic_agent to be called exactly 2 times, got {call_count}"
        )

        has_auto_approve_msg = False
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if (
                        part.text
                        and "Critic validation threshold reached. Response auto-approved."
                        in part.text
                    ):
                        has_auto_approve_msg = True
                        break
        assert has_auto_approve_msg, (
            "Expected auto-approve message in the output stream."
        )

        session_after = session_service.get_session_sync(
            session_id=session.id, user_id="test_user", app_name="test"
        )
        has_revision_event = False
        for event in session_after.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and "Critic's Feedback:" in part.text:
                        has_revision_event = True
                        break
        assert has_revision_event, (
            "Expected a user revision event in session history containing critic feedback."
        )
