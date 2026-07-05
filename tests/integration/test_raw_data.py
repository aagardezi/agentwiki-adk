# Copyright 2026 Google LLC
import os

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import storage
from google.genai import types

from app.agent import root_agent
from app.config import WIKI_BUCKET_NAME


def clean_gcs_prefixed_files(prefix: str):
    client = storage.Client()
    bucket = client.bucket(WIKI_BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix=prefix))
    for blob in blobs:
        blob.delete()


def test_raw_data_ingestion_and_query() -> None:
    temp_file = "/tmp/integration_test_doc_antigravity.txt"
    unique_token = "ANTIGRAVITY_UNIQUE_TOKEN_12345"
    content_str = f"This is an integration test document for Antigravity Wiki Agent. Secret token: {unique_token}."
    with open(temp_file, "w") as f:
        f.write(content_str)

    clean_gcs_prefixed_files("raw_data/integration_test_doc_antigravity")

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    print("=== RUNNING INGESTION ===")
    ingest_msg = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text=f"Please ingest the local file {temp_file} into the wiki."
            )
        ],
    )

    events = list(
        runner.run(
            new_message=ingest_msg,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print("[Ingest Agent Response]:", part.text)
                if part.function_call:
                    print(
                        "[Ingest Tool Call]:",
                        part.function_call.name,
                        part.function_call.args,
                    )
        if hasattr(event, "content") and event.content and event.content.role == "user":
            print("[Ingest Tool Response]:", event.content)

    client = storage.Client()
    bucket = client.bucket(WIKI_BUCKET_NAME)
    raw_blob = bucket.blob("raw_data/integration_test_doc_antigravity.txt")

    try:
        assert raw_blob.exists(), "Raw file was not copied to GCS raw_data/ folder"

        print("=== RUNNING QUERY ===")
        query_msg = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="What is the secret token of the integration test document?"
                )
            ],
        )

        events_query = list(
            runner.run(
                new_message=query_msg,
                user_id="test_user",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )

        answer = ""
        for event in events_query:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print("[Query Agent Response]:", part.text)
                        answer += part.text
                    if part.function_call:
                        print(
                            "[Query Tool Call]:",
                            part.function_call.name,
                            part.function_call.args,
                        )
            if (
                hasattr(event, "content")
                and event.content
                and event.content.role == "user"
            ):
                print("[Query Tool Response]:", event.content)

        print("=== QUERY ANSWER ===")
        print(answer)
        assert unique_token in answer, (
            f"Agent did not retrieve raw file content. Answer: {answer}"
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if raw_blob.exists():
            raw_blob.delete()
        # Find sources files created during test and clean them
        blobs = list(bucket.list_blobs(prefix="sources/"))
        for blob in blobs:
            if "integration_test_doc_antigravity" in blob.name:
                blob.delete()


def test_raw_data_inline_ingestion_and_query() -> None:
    unique_token = "ANTIGRAVITY_INLINE_TOKEN_999"
    filename = "inline test doc antigravity.txt"
    content_bytes = f"This is an inline upload integration test document. Secret inline token: {unique_token}.".encode()

    clean_gcs_prefixed_files("raw_data/inline_test_doc_antigravity")

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    print("=== RUNNING INLINE INGESTION ===")
    text_part = types.Part.from_text(
        text="Please ingest the uploaded file into the wiki."
    )
    inline_part = types.Part(
        inline_data=types.Blob(
            data=content_bytes, mime_type="text/plain", display_name=filename
        )
    )
    ingest_msg = types.Content(role="user", parts=[text_part, inline_part])

    events = list(
        runner.run(
            new_message=ingest_msg,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print("[Ingest Agent Response]:", part.text)
                if part.function_call:
                    print(
                        "[Ingest Tool Call]:",
                        part.function_call.name,
                        part.function_call.args,
                    )

    client = storage.Client()
    bucket = client.bucket(WIKI_BUCKET_NAME)
    sanitized_filename = "inline_test_doc_antigravity.txt"
    raw_blob = bucket.blob(f"raw_data/{sanitized_filename}")

    try:
        assert raw_blob.exists(), "Raw file was not copied to GCS raw_data/ folder"
        assert raw_blob.download_as_bytes() == content_bytes, (
            "GCS copy content does not match original bytes"
        )

        print("=== RUNNING QUERY ===")
        query_msg = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="What is the secret inline token of the inline test document?"
                )
            ],
        )

        events_query = list(
            runner.run(
                new_message=query_msg,
                user_id="test_user",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )

        answer = ""
        for event in events_query:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print("[Query Agent Response]:", part.text)
                        answer += part.text
                    if part.function_call:
                        print(
                            "[Query Tool Call]:",
                            part.function_call.name,
                            part.function_call.args,
                        )

        print("=== QUERY ANSWER ===")
        print(answer)
        assert unique_token in answer, (
            f"Agent did not retrieve inline raw file content. Answer: {answer}"
        )
    finally:
        if raw_blob.exists():
            raw_blob.delete()
        # Find sources files created during test and clean them
        blobs = list(bucket.list_blobs(prefix="sources/"))
        for blob in blobs:
            if "inline_test_doc_antigravity" in blob.name:
                blob.delete()
