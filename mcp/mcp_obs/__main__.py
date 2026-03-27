"""Entry point for running the observability MCP server."""

import asyncio

from mcp_obs.server import main

if __name__ == "__main__":
    asyncio.run(main())
