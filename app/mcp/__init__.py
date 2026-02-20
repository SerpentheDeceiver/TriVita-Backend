"""
MCP package — Model Context Protocol integration for TriVita Health AI.

Public API:
    from app.mcp import get_mcp_client, MCPHealthClient
"""
from app.mcp.client import MCPHealthClient, get_mcp_client

__all__ = ["MCPHealthClient", "get_mcp_client"]
