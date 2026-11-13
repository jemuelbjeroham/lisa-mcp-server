# lisa-mcp-server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that gives
the [LISA](https://github.com/jemuelbjeroham/LISA) agents their tools: internal
knowledge-base search, web search, and Jira ticket operations.

LISA launches this server as a **stdio subprocess** and talks to it through an MCP
client session. There is no separate network service or container for it; in
Docker it runs inside the `lisa-api` image. See the
[LISA README](https://github.com/jemuelbjeroham/LISA#system-overview) for the full
system diagram.

---

## Table of contents

- [Tools](#tools)
- [Write safety](#write-safety)
- [Project layout](#project-layout)
- [Requirements](#requirements)
- [Running the server](#running-the-server)
- [Configuration](#configuration)
- [Testing](#testing)
- [Adding a tool](#adding-a-tool)
- [Continuous integration](#continuous-integration)

---

## Tools

| Tool | Kind | Backend | Description |
| --- | --- | --- | --- |
| `health_check` | Read | — | Confirms the server is running |
| `search_knowledge(query, top_k=5)` | Read | `net-tools-app` `POST /api/v1/search` | Searches the internal knowledge base (document text, image OCR and macro evidence) and returns reranked chunks, grouped context and source URLs. `top_k` is accepted for compatibility; the backend applies a fixed per-category policy |
| `web_search(query, count=5)` | Read | Tavily | Ranked web results without page content |
| `web_search_with_content(query, count=5)` | Read | Tavily | Web results including raw page content |
| `search_jira_tickets(jql, max_results=20, next_page_token=None)` | Read | `net-tools-app` `POST /api/v1/jira/search` | JQL search returning tickets with description, status, priority, labels and all comments (newest first) |
| `create_jira_ticket(subject, description, project_key?, issue_type?, priority?, labels?)` | Write | Approval workflow | Proposes a new ticket. `project_key` and `issue_type` fall back to the backend defaults |
| `update_jira_ticket(ticket_key, comment)` | Write | Approval workflow | Proposes adding a comment to a ticket |
| `close_ticket(ticket_id)` | Write | Approval workflow | Proposes transitioning a ticket to Closed |

Tool descriptions are written for the model: they state what each tool does,
what it returns, and what it will not do (for example, no ticket assignment).

## Write safety

The three Jira write tools **never call Jira from this server**. Each handler
returns an error result:

```json
{"accepted": false, "error": "approval_required"}
```

LISA intercepts write calls *before* they reach this server and turns them into
approval proposals. After a person approves and explicitly resumes the action,
LISA executes it through its own authenticated adapter to `net-tools-app`, using a
signed, single-use execution capability. The client in
[`net_tools_client.py`](src/lisa_mcp_server/net_tools_client.py) enforces the same
rule: it only sends `POST /api/v1/jira/search`, and refuses any other Jira path
without making a network request. It never forwards service tokens or execution
capabilities from the environment or from tool arguments.

Do not remove these denials; they are the last line of defence if a write call
bypasses LISA's guardrail.

## Project layout

```text
src/lisa_mcp_server/
├── server.py            # MCP server and tool definitions (entry point)
├── net_tools_client.py  # HTTP client for net-tools-app (knowledge + Jira search)
└── internet_client.py   # Tavily web-search client
tests/
├── test_jira_tools.py        # Tool registration, schemas, write denials, client routes
├── test_knowledge_wiring.py  # search_knowledge request/response contract
└── test_server.py            # End-to-end stdio test (needs a live net-tools-app)
```

## Requirements

- Python **3.14+** and [uv](https://docs.astral.sh/uv/)
- A Tavily API key (required at startup)
- A reachable [`net-tools-app`](https://github.com/jemuelbjeroham/net-tools-app)
  for knowledge and Jira search

## Running the server

LISA starts the server automatically using `LISA_MCP_SERVER_COMMAND`,
`LISA_MCP_SERVER_ARGS` and `LISA_MCP_SERVER_CWD` (see the LISA README). To run it
by hand:

```sh
uv sync
TAVILY_API_KEY=<your-key> NET_TOOLS_API_URL=http://127.0.0.1:8000 \
  uv run python -m lisa_mcp_server.server
```

The server speaks MCP over stdin/stdout, so it waits for a client. To explore the
tools interactively, use the MCP Inspector from the `mcp[cli]` extra:

```sh
uv run mcp dev src/lisa_mcp_server/server.py
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `TAVILY_API_KEY` | — (required) | Tavily API key for the web-search tools; the server fails to start without it |
| `NET_TOOLS_API_URL` | `http://127.0.0.1:8000` | Base URL of `net-tools-app` |

Timeouts: knowledge search waits up to 60 seconds (retrieval loads several
collections and a reranker), Jira search 40 seconds, web search 30 seconds.

## Testing

```sh
TAVILY_API_KEY=dummy uv run pytest --deselect tests/test_server.py::test_search_knowledge_tool
uv run ruff check src tests
```

The unit tests mock all HTTP traffic. `tests/test_server.py` is an end-to-end
test: it starts the server over stdio and calls `search_knowledge`, so it needs a
real `TAVILY_API_KEY` in the environment and a running `net-tools-app` with an
indexed knowledge base.

## Adding a tool

1. Add an `@mcp.tool()` function in `server.py` with a precise docstring; the
   docstring is what the model reads.
2. Put any HTTP calls in a client class, with explicit timeouts.
3. Register the tool in LISA's HITL policy
   (`LISA/src/lisa/guardrails/hitl/policy.py`) and, if a restricted agent should
   use it, in `LISA/src/lisa/agents/tool_access.py`. Unregistered tools are
   rejected by LISA.
4. If the tool writes anything, make the handler deny execution and route the
   write through LISA's approval workflow.
5. Add tests for the schema, arguments and failure behaviour.

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) calls the shared
`python-ci.yml` workflow from
[`lisa-cicd`](https://github.com/jemuelbjeroham/lisa-cicd) (pinned to a commit
SHA), which installs the locked dependencies and builds the package on Python
3.14. Lint and test steps are currently disabled in the shared workflow, so run
them locally before pushing.
