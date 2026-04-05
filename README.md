# MCP Toolbox Server

A Model Context Protocol (MCP) server that exposes SQL tools over the Olist e-commerce database, enabling Claude Desktop to query business data through natural language.

## Architecture

```
Claude Desktop
  └─ mcp-remote ──► toolbox:5000/mcp[/{toolset}]
                         └─ Supabase (PostgreSQL)
```

[Google's MCP Toolbox](https://github.com/googleapis/genai-toolbox) acts as the MCP backend — it reads YAML tool definitions and exposes them as MCP-compatible endpoints. Claude Desktop connects via `mcp-remote`.

## Quick Start

```bash
cp tools/.env.example tools/.env   # fill in DB credentials
docker compose up
```

Then copy `claude_desktop_config.example.json` into `%APPDATA%\Claude\claude_desktop_config.json` and restart Claude Desktop.

## Endpoints

| URL | Description |
|-----|-------------|
| `http://localhost:5000/mcp` | MCP endpoint — default toolset |
| `http://localhost:5000/mcp/{toolset}` | MCP endpoint — specific toolset |
| `http://localhost:5000/ui` | Toolbox UI for testing tools |
| `http://localhost:5000/api/toolset/` | REST — list toolsets |

## Project Structure

```
mcp-toolbox-server/
├── docker-compose.yml
├── claude_desktop_config.example.json
│
├── tools/                    ← Toolbox config (volume-mounted)
│   ├── .env.example          ← DB credentials template
│   ├── source.yaml           ← DB connection (olist-db)
│   ├── toolsets.yaml         ← Toolset registry
│   └── orders.yaml           ← Tool definitions: orders department
│
└── bridge/                   ← Legacy MCP SSE bridge (not used in prod)
```

## Adding Tools

1. Create or edit a YAML file under `tools/` (e.g. `tools/customers.yaml`)
2. Define a tool:

```yaml
tools:
  get_customers_by_city:
    kind: postgres-sql
    source: olist-db
    description: Get customers filtered by city
    parameters:
      - name: city
        type: string
        description: City name
    statement: |
      SELECT * FROM customers WHERE customer_city = $1
```

3. Register it in `tools/toolsets.yaml`
4. Toolbox auto-reloads within 3 seconds

## Tech Stack

- [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) — Google's MCP backend
- [Supabase](https://supabase.com) — PostgreSQL hosting
- [mcp-remote](https://github.com/geelen/mcp-remote) — SSE-to-stdio bridge for Claude Desktop
- Docker Compose
