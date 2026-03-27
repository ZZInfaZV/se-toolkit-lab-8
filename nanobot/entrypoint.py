#!/usr/bin/env python3
"""
Entrypoint for nanobot Docker deployment.

Resolves environment variables into config.json at runtime,
then launches `nanobot gateway`.
"""

import json
import os
import sys


def resolve_config():
    """Read config.json, inject env var values, write config.resolved.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    resolved_path = os.path.join(os.path.dirname(__file__), "config.resolved.json")
    workspace_dir = os.path.join(os.path.dirname(__file__), "workspace")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Resolve LLM provider API key and base URL from env vars
    if "custom" in config.get("providers", {}):
        llm_api_key = os.environ.get("LLM_API_KEY")
        llm_base_url = os.environ.get("LLM_API_BASE_URL")
        llm_model = os.environ.get("LLM_API_MODEL")

        if llm_api_key:
            config["providers"]["custom"]["apiKey"] = llm_api_key
        if llm_base_url:
            config["providers"]["custom"]["apiBase"] = llm_base_url
        if llm_model:
            config["agents"]["defaults"]["model"] = llm_model

    # Resolve MCP server environment variables
    if "tools" in config and "mcpServers" in config["tools"]:
        if "lms" in config["tools"]["mcpServers"]:
            backend_url = os.environ.get("NANOBOT_LMS_BACKEND_URL")
            api_key = os.environ.get("NANOBOT_LMS_API_KEY")

            if backend_url:
                config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_BACKEND_URL"] = backend_url
            if api_key:
                config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = api_key

        if "obs" in config["tools"]["mcpServers"]:
            victorialogs_url = os.environ.get("VICTORIALOGS_URL")
            victoriatraces_url = os.environ.get("VICTORIATRACES_URL")

            if victorialogs_url:
                config["tools"]["mcpServers"]["obs"]["env"]["VICTORIALOGS_URL"] = victorialogs_url
            if victoriatraces_url:
                config["tools"]["mcpServers"]["obs"]["env"]["VICTORIATRACES_URL"] = victoriatraces_url

    # Write resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    return resolved_path, workspace_dir


def main():
    resolved_config, workspace = resolve_config()

    # Get gateway port from env (default to 18790)
    gateway_port = os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT", "18790")

    # Launch nanobot gateway with resolved config and port
    os.execvp("nanobot", [
        "nanobot",
        "gateway",
        "--config", resolved_config,
        "--workspace", workspace,
        "--port", gateway_port,
    ])


if __name__ == "__main__":
    main()
