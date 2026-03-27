"""Stdio MCP server exposing observability tools for VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any
from datetime import datetime, timedelta, timezone

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

server = Server("obs")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_victorialogs_url: str = ""
_victoriatraces_url: str = ""


def _get_victorialogs_url() -> str:
    """Get VictoriaLogs base URL from environment or default."""
    return os.environ.get("VICTORIALOGS_URL", "http://victorialogs:9428")


def _get_victoriatraces_url() -> str:
    """Get VictoriaTraces base URL from environment or default."""
    return os.environ.get("VICTORIATRACES_URL", "http://victoriatraces:10428")


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class _LogsSearchQuery(BaseModel):
    query: str = Field(
        default="",
        description="LogsQL query string. Example: '_stream:{service=\"backend\"} AND level:error'",
    )
    limit: int = Field(default=30, ge=1, le=1000, description="Max entries to return (default 30).")
    start: str = Field(
        default="",
        description="Start time (ISO 8601 or relative like '1h', '30m'). Default: 1 hour ago.",
    )
    end: str = Field(
        default="",
        description="End time (ISO 8601 or relative). Default: now.",
    )


class _LogsErrorCountQuery(BaseModel):
    service: str = Field(default="", description="Service name to filter (e.g., 'backend'). Empty = all services.")
    window: str = Field(default="1h", description="Time window (e.g., '1h', '30m', '24h'). Default: 1 hour.")


class _TracesListQuery(BaseModel):
    service: str = Field(default="backend", description="Service name to filter traces.")
    limit: int = Field(default=10, ge=1, le=100, description="Max traces to return (default 10).")
    min_duration: str = Field(default="", description="Minimum duration filter (e.g., '100ms', '1s').")


class _TracesGetQuery(BaseModel):
    trace_id: str = Field(..., description="Trace ID to fetch.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text(data: Any) -> list[TextContent]:
    """Serialize data to JSON text."""
    if isinstance(data, (dict, list)):
        content = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        content = str(data)
    return [TextContent(type="text", text=content)]


async def _http_get(url: str, params: dict[str, Any] | None = None, stream: bool = False) -> dict[str, Any] | list[Any]:
    """Make an HTTP GET request and return JSON response.
    
    If stream=True, parses newline-delimited JSON (VictoriaLogs format).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        if stream:
            # Parse newline-delimited JSON
            lines = response.text.strip().split('\n')
            results = []
            for line in lines:
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        results.append(line)
            return results
        return response.json()


def _parse_relative_time(relative: str) -> str:
    """Convert relative time like '1h', '30m' to VictoriaLogs format."""
    if not relative:
        return ""
    # VictoriaLogs accepts relative time directly
    if relative.endswith(("h", "m", "s", "d", "w")):
        return relative
    return relative


# ---------------------------------------------------------------------------
# VictoriaLogs tool handlers
# ---------------------------------------------------------------------------


async def _logs_search(args: _LogsSearchQuery) -> list[TextContent]:
    """Search logs using VictoriaLogs LogsQL query API."""
    base_url = _get_victorialogs_url()

    # Build query - use service.name for OpenTelemetry logs
    query = args.query or '_stream:{service.name="Learning Management Service"}'
    limit = args.limit
    start = _parse_relative_time(args.start) or "1h"
    end = _parse_relative_time(args.end) or ""

    # VictoriaLogs query endpoint
    url = f"{base_url}/select/logsql/query"
    params = {
        "query": query,
        "limit": limit,
        "start": start,
        "end": end,
    }

    try:
        result = await _http_get(url, params, stream=True)
        # VictoriaLogs returns newline-delimited JSON lines
        if isinstance(result, list):
            # Simplify the response - extract key fields
            entries = []
            for entry in result[:limit]:
                if isinstance(entry, dict):
                    entries.append({
                        "timestamp": entry.get("_time", ""),
                        "level": entry.get("severity", entry.get("level", "")),
                        "event": entry.get("event", entry.get("_msg", "")),
                        "message": entry.get("event", entry.get("_msg", "")),
                        "trace_id": entry.get("trace_id", entry.get("otelTraceID", "")),
                        "span_id": entry.get("span_id", entry.get("otelSpanID", "")),
                        "service": entry.get("service.name", entry.get("otelServiceName", "")),
                    })
            return _text({"entries": entries, "total": len(entries)})
        return _text(result)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaLogs API error: {type(e).__name__}: {e}"})
    except Exception as e:
        return _text({"error": f"Error: {type(e).__name__}: {e}"})


async def _logs_error_count(args: _LogsErrorCountQuery) -> list[TextContent]:
    """Count errors per service over a time window."""
    base_url = _get_victorialogs_url()
    window = _parse_relative_time(args.window) or "1h"

    # Build query to count errors - use severity for OpenTelemetry logs
    if args.service:
        query = f'_stream:{{service.name="{args.service}"}} AND (severity:"ERROR" OR severity:"error" OR status:"5*")'
    else:
        query = '_stream:* AND (severity:"ERROR" OR severity:"error" OR status:"5*")'

    url = f"{base_url}/select/logsql/query"
    params = {
        "query": query,
        "limit": 1000,
        "start": window,
    }

    try:
        result = await _http_get(url, params, stream=True)

        # Count errors by service
        error_counts: dict[str, int] = {}
        if isinstance(result, list):
            for entry in result:
                if isinstance(entry, dict):
                    service = entry.get("service.name", entry.get("otelServiceName", args.service or "unknown"))
                    error_counts[service] = error_counts.get(service, 0) + 1

        summary = {
            "window": window,
            "total_errors": sum(error_counts.values()),
            "by_service": error_counts,
        }
        return _text(summary)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaLogs API error: {type(e).__name__}: {e}"})
    except Exception as e:
        return _text({"error": f"Error: {type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# VictoriaTraces tool handlers
# ---------------------------------------------------------------------------


async def _traces_list(args: _TracesListQuery) -> list[TextContent]:
    """List recent traces for a service using VictoriaTraces Jaeger API."""
    base_url = _get_victoriatraces_url()
    
    # VictoriaTraces Jaeger-compatible API
    url = f"{base_url}/jaeger/api/traces"
    params = {
        "service": args.service,
        "limit": args.limit,
    }
    
    if args.min_duration:
        params["minDuration"] = args.min_duration
    
    try:
        result = await _http_get(url, params)
        
        # Simplify the response
        traces = []
        if isinstance(result, dict) and "data" in result:
            for trace in result["data"]:
                traces.append({
                    "trace_id": trace.get("traceID"),
                    "span_count": len(trace.get("spans", [])),
                    "start_time": trace.get("startTime"),
                    "duration": trace.get("duration"),
                    "service": args.service,
                })
        
        return _text({"traces": traces, "total": len(traces)})
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaTraces API error: {type(e).__name__}: {e}"})
    except Exception as e:
        return _text({"error": f"Error: {type(e).__name__}: {e}"})


async def _traces_get(args: _TracesGetQuery) -> list[TextContent]:
    """Fetch a specific trace by ID using VictoriaTraces Jaeger API."""
    base_url = _get_victoriatraces_url()
    trace_id = args.trace_id
    
    url = f"{base_url}/jaeger/api/traces/{trace_id}"
    
    try:
        result = await _http_get(url)
        
        # Simplify the response
        if isinstance(result, dict) and "data" in result:
            traces = result["data"]
            if traces:
                trace = traces[0]
                spans = trace.get("spans", [])
                span_summary = [
                    {
                        "span_id": s.get("spanID"),
                        "operation": s.get("operationName"),
                        "service": s.get("process", {}).get("serviceName"),
                        "duration": s.get("duration"),
                        "tags": len(s.get("tags", [])),
                    }
                    for s in spans[:20]  # Limit to first 20 spans
                ]
                return _text({
                    "trace_id": trace.get("traceID"),
                    "span_count": len(spans),
                    "spans": span_summary,
                    "services": list(set(s.get("process", {}).get("serviceName") for s in spans)),
                })
        return _text(result)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaTraces API error: {type(e).__name__}: {e}"})
    except Exception as e:
        return _text({"error": f"Error: {type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# Registry: tool name -> (input model, handler, Tool definition)
# ---------------------------------------------------------------------------

_Registry = tuple[type[BaseModel], Callable[..., Awaitable[list[TextContent]]], Tool]

_TOOLS: dict[str, _Registry] = {}


def _register(
    name: str,
    description: str,
    model: type[BaseModel],
    handler: Callable[..., Awaitable[list[TextContent]]],
) -> None:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    schema.pop("title", None)
    _TOOLS[name] = (
        model,
        handler,
        Tool(name=name, description=description, inputSchema=schema),
    )


_register(
    "logs_search",
    "Search logs in VictoriaLogs using LogsQL. Use to find errors, debug info, or trace IDs.",
    _LogsSearchQuery,
    _logs_search,
)
_register(
    "logs_error_count",
    "Count errors per service over a time window. Use to quickly check system health.",
    _LogsErrorCountQuery,
    _logs_error_count,
)
_register(
    "traces_list",
    "List recent traces for a service. Shows trace IDs, duration, and span count.",
    _TracesListQuery,
    _traces_list,
)
_register(
    "traces_get",
    "Fetch a specific trace by ID. Shows span hierarchy and timing details.",
    _TracesGetQuery,
    _traces_get,
)


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [entry[2] for entry in _TOOLS.values()]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    entry = _TOOLS.get(name)
    if entry is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    model_cls, handler, _ = entry
    try:
        args = model_cls.model_validate(arguments or {})
        return await handler(args)
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    global _victorialogs_url, _victoriatraces_url
    _victorialogs_url = _get_victorialogs_url()
    _victoriatraces_url = _get_victoriatraces_url()
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
