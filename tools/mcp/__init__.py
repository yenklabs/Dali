"""Dali MCP contributor tools.

Exposes four tools via the Model Context Protocol so contributors can
validate, scaffold, and bundle corpus records and synthetic prompts
directly from Claude or any MCP-capable editor, without running
terminal commands.

Usage:
    python -m tools.mcp   (starts the MCP server on stdio)

See tools/mcp/README.md for Claude Desktop and editor setup.
"""

__version__ = "0.2.0"
