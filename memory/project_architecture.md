---
name: Toolbox MCP Server Architecture
description: Dev and prod flow for the olist toolbox MCP server project
type: project
---

Two flows in toolbox-mcp-server:

**Dev flow:** `python .claude/scripts/query_db.py "<SQL>" [conn_name]` → `connections.conf` → SQLAlchemy → Supabase

**Prod flow:** Claude Desktop → `mcp-remote` → `toolbox:5000/mcp[/{toolset}]` → Supabase (via pooler)

The `bridge/` directory exists but is **legacy** — prod connects directly to toolbox's native `/mcp` endpoint, no bridge needed.

**Why:** Toolbox v0.31+ has native StreamableHTTP MCP endpoint at `/mcp`. The bridge (SSE) was built before this was discovered.

**How to apply:** Don't modify bridge unless explicitly asked. All prod work goes through toolbox directly.
