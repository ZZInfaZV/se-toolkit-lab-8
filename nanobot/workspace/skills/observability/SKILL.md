# Observability Skill

You have access to observability tools that let you query **VictoriaLogs** and **VictoriaTraces**. Use these tools to investigate system health, find errors, and trace request failures.

## Available Tools

### Log Tools (VictoriaLogs)

- **`logs_search`** — Search logs using LogsQL queries
  - Use when: User asks about specific errors, events, or trace IDs
  - Parameters:
    - `query`: LogsQL query (e.g., `_stream:{service.name="Learning Management Service"} AND severity:ERROR`)
    - `limit`: Max entries (default 30)
    - `start`: Start time like "1h", "30m" (default: 1 hour ago)
    - `end`: End time (default: now)

- **`logs_error_count`** — Count errors per service over a time window
  - Use when: User asks "any errors?", "system health", "error summary"
  - Parameters:
    - `service`: Filter by service name (optional, empty = all services). Use "Learning Management Service" for the LMS backend.
    - `window`: Time window like "1h", "30m", "24h" (default: 1h)

### Trace Tools (VictoriaTraces)

- **`traces_list`** — List recent traces for a service
  - Use when: User wants to see recent request traces
  - Parameters:
    - `service`: Service name (default: "backend")
    - `limit`: Max traces (default: 10)
    - `min_duration`: Filter by minimum duration (optional)

- **`traces_get`** — Fetch a specific trace by ID
  - Use when: You found a trace ID in logs and need full details
  - Parameters:
    - `trace_id`: The trace ID to fetch (required)

## Strategy

### When the user asks about errors or system health

1. **Start with `logs_error_count`** — Get a quick summary of errors across services
2. **If errors found, use `logs_search`** — Find specific error details
3. **If you find a trace ID in the logs, use `traces_get`** — Fetch the full trace to see the failure point

### When the user asks about a specific request

1. **Use `logs_search`** — Find logs matching the request (by time, endpoint, or trace ID)
2. **Extract the trace ID** — Look for `trace_id=xxx` in log entries
3. **Use `traces_get`** — Fetch the full trace to see the span hierarchy and timing

### When the user asks "what went wrong?" or "check system health"

This is a **one-shot investigation** — chain the tools together in a single coherent response:

1. **Call `logs_error_count`** with `window="5m"` or `window="1h"` — Check for recent errors and identify which service is affected
   - For LMS backend errors, use `service="Learning Management Service"`
2. **Call `logs_search`** with a query targeting the affected service — Search for error-level logs to find:
   - The error message
   - The timestamp
   - A trace ID (look for `trace_id` or `otelTraceID` field in the log entry)
   - Use query: `_stream:{service.name="Learning Management Service"} AND severity:ERROR`
3. **If you found a trace ID, call `traces_get`** — Fetch the full trace to see:
   - The span hierarchy (which operations were called)
   - Which span failed (look for error tags or status=ERROR)
   - The root cause (database connection failure, timeout, etc.)
4. **Summarize findings concisely** — Report:
   - **What failed**: The operation or endpoint
   - **When**: Timestamp of the failure
   - **Why**: The root cause error message
   - **Evidence**: Reference both log and trace data
   - **Trace ID**: Include for further investigation

**Example response format:**
```
🔴 **System Failure Detected**

**What**: Backend `/items/` endpoint returned 500
**When**: 2 minutes ago (14:32:15 UTC)
**Why**: PostgreSQL connection refused — database is down

**Evidence**:
- Logs: Found 3 errors in Learning Management Service with "connection refused"
- Trace: `abc123...` shows db_query span failed with status=ERROR

The backend cannot reach PostgreSQL. Check if the database container is running.
```

## Response Format

- **Be concise** — Lead with the answer, then provide details
- **Summarize, don't dump** — Don't paste raw JSON; explain what it means
- **Highlight key info** — Error messages, trace IDs, timestamps, affected services
- **Use markdown** — Format tables and code blocks for readability

## Examples

**User:** "Any errors in the last hour?"

**You:** Call `logs_error_count` with `window="1h"` and `service="Learning Management Service"`. Report:
- Total error count
- Which services had errors
- Most common error types (if visible)

**User:** "Show me errors from the backend"

**You:** Call `logs_search` with `query='_stream:{service.name="Learning Management Service"} AND severity:ERROR'` and `limit=20`. Summarize the error messages found.

**User:** "What happened to request abc123?"

**You:** Call `traces_get` with `trace_id="abc123"`. Show the span hierarchy, highlight any error spans, and report total duration.

**User:** "What went wrong?"

**You:** 
1. Call `logs_error_count` — find errors exist
2. Call `logs_search` — find specific error details
3. If trace ID found, call `traces_get` — get full context
4. Report: "The backend failed to connect to PostgreSQL at [time]. Error: [message]. Trace ID: [id]."
