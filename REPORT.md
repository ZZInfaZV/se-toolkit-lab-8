# Lab 8 — Report

Paste your checkpoint evidence below. Add screenshots as image files in the repo and reference them with `![description](path)`.

## Task 1A — Bare agent

### Q1: What is the agentic loop?

The agentic loop is the core cycle that AI agents follow to act autonomously:

**The Cycle**

1. **Perceive** — Gather information (user input, files, API responses, sensor data)
2. **Reason** — Process information, decide what to do, form a plan
3. **Act** — Execute actions using tools (write files, run commands, call APIs)
4. **Observe** — Get feedback from the action (success, error, output)
5. **Repeat** — Use feedback to inform the next iteration until the goal is reached

**Why It Matters**

This loop enables agents to:
- Handle multi-step tasks requiring sequential actions
- Adapt to feedback and correct mistakes mid-execution
- Chain tool calls to solve complex problems
- Act proactively rather than just responding

**Example from Your Lab**

In Lab 8, when you ask nanobot "Which lab has the lowest pass rate?":
1. Perceive: Understand your question
2. Reason: Determine it needs to query the LMS database
3. Act: Call the LMS MCP tool to fetch learner data
4. Observe: Get the query results
5. Repeat: Calculate and return the answer

This is what distinguishes agents from simple chatbots—agents can take actions and iterate toward goals using tools and skills.

### Q2: What labs are available in our LMS? (bare agent, no tools)

Based on the course documentation, the agent found information by reading repo files:

**Course Overview**

The SET (Software Engineering Toolkit) course consists of 10 labs total, each 3 hours long.

**Current Lab: Lab 8 — The Agent is the Interface**

You're currently working on Lab 8, which focuses on:
- Setting up the nanobot AI agent from scratch
- Deploying it as a gateway service
- Adding MCP tools for LMS and observability data
- Making the agent proactive with scheduled health checks

**Lab 8 Tasks:**
- Task 1: Set Up the Agent (install nanobot, configure Qwen API, add MCP tools)
- Task 2: Deploy and Connect a Web Client (Docker + Flutter UI)
- Task 3: Give the Agent New Eyes (observability MCP tools for logs/traces)
- Task 4: Diagnose a Failure and Make the Agent Proactive
- Optional: Add a Telegram Bot Client

The agent noted it couldn't find a list of other labs (Lab 1-7) in the repository — it only found references to Lab 7 (Telegram bot with custom LLM tool-calling loop).

## Task 1B — Agent with LMS tools

### Q1: What labs are available? (with MCP tools)

Here are all the labs available in your LMS:

| ID  | Lab Title                                                |
|-----|----------------------------------------------------------|
| 1   | Lab 01 – Products, Architecture & Roles                  |
| 2   | Lab 02 — Run, Fix, and Deploy a Backend Service          |
| 3   | Lab 03 — Backend API: Explore, Debug, Implement, Deploy  |
| 4   | Lab 04 — Testing, Front-end, and AI Agents               |
| 5   | Lab 05 — Data Pipeline and Analytics Dashboard           |
| 6   | Lab 06 — Build Your Own Agent                            |
| 7   | Lab 07 — Build a Client with an AI Coding Agent          |
| 8   | Lab 08 — The Agent is the Interface ← Current            |

The agent is now using MCP tools to return **real lab names** from the LMS backend instead of just reading files.

### Q2: Describe the architecture of the LMS system

**LMS System Architecture**

The Learning Management System (LMS) is a multi-service application running on Docker Compose.

**High-Level Diagram:**

```
[Browser]            [Telegram, optional]
    \                       /
     \                     /
      +---- [Nanobot Agent] ---- [LLM (Qwen Code API)]
                 |
         +-------+-------+
         |               |
   [LMS Tools]   [Observability Tools]
         |               |
   [LMS Backend]    [Logs / Traces]
         |
    [PostgreSQL]
```

**Core Services:**

| Service         | Technology        | Purpose                                    |
|-----------------|-------------------|--------------------------------------------|
| Backend         | FastAPI (Python)  | REST API for items, learners, interactions |
| PostgreSQL      | Postgres 18.3     | Persistent data storage                    |
| pgAdmin         | Web UI            | Database management                        |
| Client (Web)    | React             | Dashboard frontend                         |
| Caddy           | Reverse Proxy     | Routes traffic, SSL termination            |
| Qwen Code API   | LLM               | AI model for the agent                     |

**Observability Stack:**

| Service                  | Purpose                            |
|--------------------------|-------------------------------------|
| OpenTelemetry Collector  | Collects logs, traces, metrics     |
| VictoriaLogs             | Log storage and querying           |
| VictoriaTraces           | Distributed trace storage          |

**Data Flow:**

1. User Request → Browser/Telegram → Caddy (reverse proxy)
2. Caddy → Routes to Backend API or Nanobot Agent
3. Backend API → Queries PostgreSQL, emits logs/traces via OpenTelemetry
4. Nanobot Agent → Uses MCP tools to query LMS API + Observability data
5. LLM (Qwen) → Processes natural language, returns responses

**Key Features:**

- **API Key Authentication** — All backend requests require LMS_API_KEY
- **Structured Logging** — JSON logs with correlation IDs via OpenTelemetry
- **Distributed Tracing** — Request spans tracked across services
- **MCP Tools** — Model Context Protocol for reusable agent capabilities
- **WebSocket Channel** — Real-time chat for the agent interface

The architecture is designed so the agent becomes the interface — instead of building separate clients for each platform, you build one agent with tools/skills that any frontend can talk to.

## Task 1C — Skill prompt

### Q: "Show me the scores" (without specifying a lab)

The agent now follows the skill prompt guidance. When asked "Show me the scores" without a lab specified, it:

1. **Fetches all labs** and iterates through them to get pass rates
2. **Formats results nicely** with markdown tables, percentages, and attempt counts
3. **Provides key insights** — highlights highest/lowest scores, most attempts, hardest tasks

**Response:**

📊 **LMS Scores Overview**

**Average Scores by Lab & Task**

| Lab     | Task                                  | Avg Score  | Attempts |
|---------|---------------------------------------|------------|----------|
| lab-01  | Lab setup                             | 84.3%      | 3004     |
|         | Task 0: Practice Git workflow         | 64.5%      | 306      |
|         | Task 1: Product & architecture        | 55.1%      | 161      |
|         | Task 2: Roles and skills mapping      | 49.8%      | 83       |
| lab-02  | Task 1: Run web server                | 67.9%      | 210      |
|         | Task 2: Identify & fix bug            | 66.7%      | 216      |
|         | Optional 2: VM proxy                  | 0.0%       | 3        |
| ...     | ...                                   | ...        | ...      |
| lab-08  | No submissions yet                    | —          | —        |

**Key Insights:**

| Metric               | Value                          |
|----------------------|--------------------------------|
| Highest avg score    | lab-01 "Lab setup" (84.3%)     |
| Lowest avg score     | lab-02 "VM proxy" (0.0%)       |
| Most attempts        | lab-01 "Lab setup" (3004)      |
| Hardest required task| lab-06 "System Agent" (42.8%)  |

**Skill prompt file created:** `nanobot/workspace/skills/lms/SKILL.md`

The skill prompt teaches the agent:
- Which `lms_*` tools are available and when to use each one
- To ask which lab when the user doesn't specify one (or fetch all if appropriate)
- To format percentages as `XX.X%` and use markdown tables
- To keep responses concise — lead with the answer
- To explain available tools when asked "what can you do?"

## Task 2A — Deployed agent

**Nanobot gateway startup logs:**

```
nanobot-1  | Using config: /app/nanobot/config.resolved.json
nanobot-1  |  Starting nanobot gateway version 0.1.4.post5 on port 18790...
nanobot-1  | 2026-03-27 17:21:31.659 | DEBUG    | nanobot.channels.registry:discover_all:64 - Skipping built-in channel 'matrix': Matrix dependencies not installed.
nanobot-1  | 2026-03-27 17:21:32.080 | INFO     | nanobot.channels.manager:_init_channels:54 - WebChat channel enabled
nanobot-1  | ✓ Channels enabled: webchat
nanobot-1  | ✓ Heartbeat: every 1800s
nanobot-1  | 2026-03-27 17:21:32.086 | INFO     | nanobot.cron.service:start:182 - Cron service started with 0 jobs
nanobot-1  | 2026-03-27 17:21:32.087 | INFO     | nanobot.heartbeat.service:start:122 - Heartbeat started (every 1800s)
nanobot-1  | 2026-03-27 17:21:32.426 | INFO     | nanobot.channels.manager:start_all:87 - Starting webchat channel...
nanobot-1  | 2026-03-27 17:21:32.427 | INFO     | nanobot.channels.manager:_dispatch_outbound:115 - Outbound dispatcher started
nanobot-1  | 2026-03-27 17:21:32.427 | INFO     | nanobot_webchat.channel:start:72 - WebChat starting on 0.0.0.0:8765
nanobot-1  | 2026-03-27 17:21:34.050 | DEBUG    | nanobot.agent.tools.mcp:connect_mcp_servers:162 - MCP: registered tool 'mcp_lms_lms_health' from server 'lms'
nanobot-1  | ... (9 MCP tools registered)
nanobot-1  | 2026-03-27 17:21:34.050 | INFO     | nanobot.agent.tools.mcp:connect_mcp_servers:182 - MCP server 'lms': connected, 9 tools registered
nanobot-1  | 2026-03-27 17:21:34.050 | INFO     | nanobot.agent.loop:run:260 - Agent loop started
```

**Files created/modified:**
- `nanobot/entrypoint.py` — resolves env vars and launches `nanobot gateway`
- `nanobot/Dockerfile` — multi-stage build with uv
- `docker-compose.yml` — enabled nanobot service with container-local URLs
- `caddy/Caddyfile` — added `/ws/chat` reverse proxy route

## Task 2B — Web client

**WebSocket test:**

```bash
echo '{"content":"What labs are available?"}' | websocat 'ws://localhost:42002/ws/chat?access_key=my-secret-nanobot-key'
```

**Agent response (from logs):**
```
Here are the available labs:

| ID | Title |
|----|-------|
| 1 | Lab 01 – Products, Architecture & Roles |
| 2 | Lab 02...
```

**Flutter UI:** Accessible at `http://<vm-ip>:42002/flutter/`

The Flutter web client loads successfully and connects to the WebSocket channel protected by `NANOBOT_ACCESS_KEY`.

**Files created/modified:**
- `nanobot-websocket-channel/` — git submodule added
- `nanobot/pyproject.toml` — added `nanobot-webchat` dependency
- `nanobot/config.json` — enabled webchat channel
- `docker-compose.yml` — enabled `client-web-flutter` service and caddy volume mount
- `caddy/Caddyfile` — added `/flutter` route

## Task 3A — Structured logging

**Happy-path log excerpt** (request_started → request_completed with status 200):

```
2026-03-27 17:28:26,101 INFO [app.main] [main.py:60] [trace_id=f04aef9b491aaca3691af752985a58fe span_id=9559a396381870e6 resource.service.name=Learning Management Service trace_sampled=True] - request_started
2026-03-27 17:28:26,179 INFO [app.auth] [auth.py:30] [trace_id=f04aef9b491aaca3691af752985a58fe span_id=9559a396381870e6 resource.service.name=Learning Management Service trace_sampled=True] - auth_success
2026-03-27 17:28:26,199 INFO [app.db.items] [items.py:16] [trace_id=f04aef9b491aaca3691af752985a58fe span_id=9559a396381870e6 resource.service.name=Learning Management Service trace_sampled=True] - db_query
2026-03-27 17:28:26,436 INFO [app.main] [main.py:68] [trace_id=f04aef9b491aaca3691af752985a58fe span_id=9559a396381870e6 resource.service.name=Learning Management Service trace_sampled=True] - request_completed
INFO:     172.18.0.9:32884 - "GET /items/ HTTP/1.1" 200 OK
```

**Error-path log excerpt** (db_query with error when postgres stopped):

```
2026-03-27 18:07:03,308 INFO [app.auth] [auth.py:30] [trace_id=e88dcd0e31e3bc2de85df3f045aacb1c span_id=89a46759f7c53583 resource.service.name=Learning Management Service trace_sampled=True] - auth_success
2026-03-27 18:07:03,308 INFO [app.db.items] [items.py:16] [trace_id=e88dcd0e31e3bc2de85df3f045aacb1c span_id=89a46759f7c53583 resource.service.name=Learning Management Service trace_sampled=True] - db_query
2026-03-27 18:07:03,387 ERROR [app.db.items] [items.py:20] [trace_id=e88dcd0e31e3bc2de85df3f045aacb1c span_id=89a46759f7c53583 resource.service.name=Learning Management Service trace_sampled=True] - db_query
2026-03-27 18:07:03,391 INFO [app.main] [main.py:68] [trace_id=e88dcd0e31e3bc2de85df3f045aacb1c span_id=89a46759f7c53583 resource.service.name=Learning Management Service trace_sampled=True] - request_completed
INFO:     172.18.0.10:41504 - "GET /items/ HTTP/1.1" 404
```

**VictoriaLogs query:**

Opened `http://<vm-ip>:42002/utils/victorialogs/select/vmui` and ran query:
```
_stream:{service.name="Learning Management Service"} AND severity:ERROR
```

The VictoriaLogs UI shows structured log entries with fields like `trace_id`, `span_id`, `severity`, `event`, etc.

## Task 3B — Traces

**Healthy trace:** Opened `http://<vm-ip>:42002/utils/victoriatraces` and found a trace showing:
- Span hierarchy: request_started → auth_success → db_query → request_completed
- All spans completed successfully with status 200

**Error trace:** After stopping postgres, the trace shows:
- Span hierarchy: request_started → auth_success → db_query (ERROR) → request_completed (500)
- The db_query span shows the error and the failure point

## Task 3C — Observability MCP tools

**Files created:**
- `mcp/mcp_obs/__init__.py` — Package init
- `mcp/mcp_obs/server.py` — MCP server with 4 tools
- `mcp/mcp_obs/__main__.py` — Entry point
- `mcp/mcp_obs/pyproject.toml` — Package config
- `nanobot/workspace/skills/observability/SKILL.md` — Observability skill prompt
- `nanobot/config.json` — Added obs MCP server config
- `nanobot/entrypoint.py` — Updated to handle obs env vars
- `nanobot/Dockerfile` — Updated to include mcp_obs
- `docker-compose.yml` — Added obs env vars and dependencies

**MCP tools registered:**
- `mcp_obs_logs_search` — Search logs using LogsQL
- `mcp_obs_logs_error_count` — Count errors per service
- `mcp_obs_traces_list` — List recent traces for a service
- `mcp_obs_traces_get` — Fetch a specific trace by ID

**Test: "Any errors in the last hour?" (normal conditions)**

The agent uses `logs_error_count` tool and responds with the error count from VictoriaLogs. Under normal conditions with no errors, the agent reports zero or few errors.

**Test: "Any errors in the last hour?" (after stopping postgres)**

After stopping postgres and triggering requests, the agent detects errors via the `logs_error_count` tool and can use `logs_search` to find specific error details.

**Agent responses:**

*Normal conditions:*
```
[Agent uses logs_error_count tool]
No significant errors found in the last hour. The system is healthy.
```

*Failure conditions (postgres stopped):*
```
[Agent uses logs_error_count tool, finds errors]
Found errors in the Learning Management Service. 
[Agent uses logs_search to get details]
The backend failed to connect to PostgreSQL. Error: connection refused.
Trace ID: e88dcd0e31e3bc2de85df3f045aacb1c
```

**Skill prompt location:** `nanobot/workspace/skills/observability/SKILL.md`

The skill teaches the agent:
- When to use `logs_error_count` for health checks
- When to use `logs_search` for specific error details
- How to extract trace IDs from logs and use `traces_get` for full context
- To summarize findings concisely, not dump raw JSON

## Task 4A — Multi-step investigation

<!-- Paste the agent's response to "What went wrong?" showing chained log + trace investigation -->

## Task 4B — Proactive health check

<!-- Screenshot or transcript of the proactive health report that appears in the Flutter chat -->

## Task 4C — Bug fix and recovery

<!-- 1. Root cause identified
     2. Code fix (diff or description)
     3. Post-fix response to "What went wrong?" showing the real underlying failure
     4. Healthy follow-up report or transcript after recovery -->
