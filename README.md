# ChatKit Python

ChatKit Python (published as `openai-chatkit`) is the backend SDK that powers the ChatKit UI SDK. It provides the primitives you need to accept user input, run tools or Agents, stream updates, and persist chat state in your own infrastructure. The package is framework agnostic and focuses on thread lifecycle management, streaming, widgets, and integrations with the OpenAI Agents SDK.

## Features
- Framework-agnostic `ChatKitServer` base class for handling JSON and Server-Sent Event (SSE) traffic.
- Strongly typed models for threads, messages, workflows, widgets, and actions via Pydantic.
- Helpers that translate streamed Agents SDK runs into ChatKit thread events (`stream_agent_response`, `AgentContext`).
- Widget utilities for rendering rich UI elements and progressively updating them from async generators.
- Extensible storage interfaces (`Store`, `AttachmentStore`) so you can plug in any database or blob store while keeping IDs and access control under your control.

## Installation
ChatKit targets Python 3.10 or newer.

```bash
pip install openai-chatkit
```

This repository also includes a `uv.lock` file and `Makefile` recipes (`make install`) if you prefer using [uv](https://github.com/astral-sh/uv) for dependency management.

## Quick start
1. **Provide storage implementations.** Implement the abstract methods defined on `chatkit.store.Store` (threads and thread items) and, if you want to accept uploads, `chatkit.store.AttachmentStore`. The test suite ships with an example SQLite store in `tests/helpers/mock_store.py` you can adapt.
2. **Subclass `ChatKitServer`.** Override `respond` to stream `ThreadStreamEvent` objects and optionally `action` / `add_feedback` for interactive flows.
3. **Expose an HTTP endpoint.** Call `ChatKitServer.process()` inside your web framework to handle both streaming (SSE) and non-streaming JSON requests.

Minimal echo-style server:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadMetadata,
    ThreadStreamEvent,
    ThreadItemDoneEvent,
    UserMessageItem,
)

RequestContext = dict[str, Any]


class EchoServer(ChatKitServer[RequestContext]):
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        text = ""
        if input_user_message:
            for part in input_user_message.content:
                if hasattr(part, "text"):
                    text += part.text
        yield ThreadItemDoneEvent(
            item=AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=f"Echo: {text}")],
            )
        )
```

Expose the server with any ASGI framework:

```python
from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse, JSONResponse

app = FastAPI()
server = EchoServer(store=my_store)  # my_store implements chatkit.store.Store

@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    body = await request.body()
    result = await server.process(body, context={"user_id": "123"})
    if hasattr(result, "json_events"):
        return StreamingResponse(result.json_events, media_type="text/event-stream")
    return JSONResponse(result.json)
```

The server handles message creation, storage updates, and type coercion; your `respond` implementation only needs to yield meaningful events in the order you want the ChatKit UI to render them.

## Lifecycle overview
ChatKit speaks a single POST endpoint. Incoming envelopes are validated against discriminated unions defined in `chatkit.types`:
- **Streaming operations** (`threads.create`, `threads.add_user_message`, `threads.custom_action`, etc.) invoke `_process_streaming` and emit SSE-encoded events.
- **Non-streaming operations** (`threads.list`, `threads.get_by_id`, `attachments.create`, etc.) return JSON payloads immediately.

The base class persists items for you. When you yield `ThreadItemDoneEvent`, `ThreadItemRemovedEvent`, or `ThreadItemReplacedEvent`, the helper `_process_events` writes the data via your `Store`. Hidden context items are automatically filtered from client responses but still stored for the next turn.

## Key concepts
### Threads and items
`chatkit.types` defines everything the UI understands: user messages, assistant messages, tool calls, workflows, tasks, widgets, hidden context, and metadata (`ThreadMetadata`, `Page`, `FeedbackKind`, etc.). You can use the models directly to validate inbound data or construct outbound events.

### `ChatKitServer`
Implement `respond` to orchestrate inference, tool invocations, or other business logic. Override `action` to handle `ActionConfig` payloads emitted by widgets, and optionally `add_feedback` to capture thumbs-up/thumbs-down style signals. Use `self.store.generate_thread_id` and `self.store.generate_item_id` whenever you need deterministic IDs.

`ChatKitServer.process()` returns either a `StreamingResult` (wrapping an async iterator of SSE-encoded bytes) or a `NonStreamingResult`. This makes integration with ASGI/WSGI frameworks straightforward.

### Storage interfaces
`Store[TContext]` and `AttachmentStore[TContext]` let you keep persistence and authorization in your domain. Override `generate_*_id` if you need custom prefixes or deterministic IDs. The default implementations rely on UUID4-based prefixes such as `msg_` and `thr_` (`chatkit.store.default_generate_id`).

### Actions
`chatkit.actions.Action` and `ActionConfig` wire UI interactions back to the server. Use `Action.create(payload, handler=..., loading_behavior=...)` to build configs that the frontend can attach to buttons or forms. Inside `ChatKitServer.action` you receive the action payload, the widget that triggered it (if any), and your request context so you can update state or kick off long-running work.

### Widgets and rich responses
Construct widgets with the classes in `chatkit.widgets` (`Card`, `Box`, `Markdown`, `ListView`, etc.). `chatkit.server.stream_widget` takes either a fully-formed widget or an async generator that yields incremental updates; the helper computes the minimal deltas needed by the UI (`diff_widget`). For streaming plain text, use `chatkit.agents.accumulate_text` with `Markdown` or `Text` widgets.

### Bringing in the Agents SDK
`chatkit.agents.AgentContext` keeps track of the active thread, store, workflow state, and queued events. The helper `stream_agent_response(context, result)` converts an `openai.agents` `RunResultStreaming` into ChatKit thread events, automatically handling reasoning traces, assistant messages, workflow summaries, and guardrail tripwires. `ThreadItemConverter` and its defaults (`simple_to_agent_input`) show how to map stored history into Agents SDK inputs; override it if you need custom attachment handling or richer hidden context.

## Attachments and uploads
If you wire an `AttachmentStore`, ChatKit can register files via `attachments.create`, generate upload URLs for two-phase uploads, and clean up with `attachments.delete`. Your store and attachment store both receive the request context, allowing you to enforce per-user access control before returning metadata or bytes.

## Error handling
Raise `chatkit.errors.StreamError` when you want to surface a localized, code-based error that the client can map to UI copy. Use `CustomStreamError` for bespoke, fully custom messages. Uncaught exceptions are logged via `chatkit.logger` and automatically returned as retryable `stream.error` events with a default message (`chatkit.server.DEFAULT_ERROR_MESSAGE`). Set `LOG_LEVEL` to control logging verbosity.

## Development and tooling
- **Tests:** `uv run pytest` (or `make test`). Async fixtures are configured via `pytest-asyncio`.
- **Linters & type checking:** `make format`, `make lint`, `make pyright`, `make mypy`.
- **Docs:** The `docs/` directory contains authored guides. Generated API reference pages are built with MkDocs (`make serve-docs`). `docs/gen_ref_pages.py` shows how we stitch together API docs with `mkdocs-gen-files`.
- **Packaging:** `make build` produces a wheel and sdist.

## Additional resources
- API reference and guides live under `docs/` (served with `mkdocs serve`).
- Example widgets, actions, and stores under `tests/helpers/` demonstrate end-to-end flows used in the test suite.

## License
This project is licensed under the [Apache License 2.0](LICENSE).
