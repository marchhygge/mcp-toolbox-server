"""
MCP Bridge — JSON-RPC over SSE → HTTP POST → Toolbox
"""

import os
import json
import logging

import httpx
import uvicorn
from starlette.types import Scope, Receive, Send

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bridge")

TOOLBOX_URL = os.environ.get("TOOLBOX_URL", "http://toolbox:5000").rstrip("/")
TOOLSET     = os.environ.get("TOOLSET", "default")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = Server("toolbox-bridge")
sse = SseServerTransport("/messages/")


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{TOOLBOX_URL}/api/toolset/{TOOLSET}")
        resp.raise_for_status()
        data = resp.json()

    tools = []
    for name, t in data.get("tools", {}).items():
        props = {}
        required = []
        for p in t.get("parameters", []):
            param_name = p["name"]
            props[param_name] = {"type": "string", "description": p.get("description", "")}
            if p.get("required", True):
                required.append(param_name)

        schema: dict = {"type": "object", "properties": props}
        if required:
            schema["required"] = required

        tools.append(Tool(name=name, description=t.get("description", ""), inputSchema=schema))

    log.info("Listed %d tools from toolset '%s'", len(tools), TOOLSET)
    return tools


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("Calling tool '%s' with %s", name, arguments)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{TOOLBOX_URL}/api/tool/{name}/invoke", json=arguments or {})
        resp.raise_for_status()
        result = resp.json()

    payload = result.get("result", result)
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


# ---------------------------------------------------------------------------
# Pure ASGI app — no Starlette Mount redirect
# ---------------------------------------------------------------------------
async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            event = await receive()
            if event["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif event["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope["type"] != "http":
        return

    path = scope.get("path", "")

    if path in ("/sse", "/sse/"):
        async with sse.connect_sse(scope, receive, send) as (read, write):
            await mcp.run(read, write, mcp.create_initialization_options())

    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    else:
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"Not found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
