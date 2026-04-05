# Toolbox MCP Server

## Dev Flow — Query Database Directly

```bash
python .claude/scripts/query_db.py "<SQL query>" [connection_name]
```

### Examples
```bash
python .claude/scripts/query_db.py "SELECT COUNT(*) FROM orders"
python .claude/scripts/query_db.py "SELECT * FROM orders LIMIT 5" supabase
```

### Connection Setup
Edit `.claude/scripts/connections.conf`:
```ini
[default]
url = postgresql://user:password@host:5432/dbname

[supabase]
url = postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres
```

---

## Prod Flow — Docker Compose + Toolbox

```
Claude Desktop
  └─ mcp-remote ──► toolbox:5000/mcp[/{toolset}]
                         └─ DB (Supabase via pooler)
```

### Start
```bash
cp tools/.env.example tools/.env   # fill in credentials
docker compose up
```

### Endpoints
| URL | Description |
|-----|-------------|
| `http://localhost:5000/mcp` | MCP endpoint — default toolset |
| `http://localhost:5000/mcp/{toolset}` | MCP endpoint — specific toolset |
| `http://localhost:5000/ui` | Toolbox UI for testing tools |
| `http://localhost:5000/api/toolset/` | REST API — list toolsets |

### Claude Desktop Config
Copy `claude_desktop_config.example.json` into `%APPDATA%\Claude\claude_desktop_config.json`.

---

## Project Structure

```
toolbox-mcp-server/
├── CLAUDE.md
├── docker-compose.yml
├── claude_desktop_config.example.json
├── .env                          ← TOOLS_PATH (WSL path if needed)
│
├── .claude/scripts/              ← Dev flow
│   ├── query_db.py               ← CLI query runner
│   └── connections.conf          ← DB connection URLs
│
├── bridge/                       ← MCP SSE bridge (legacy, not used in prod)
│   ├── server.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── tools/                        ← Toolbox volume mount
    ├── .env                      ← DB credentials (DB_HOST, DB_PORT, ...)
    ├── .env.example
    ├── source.yaml               ← DB connection definition (olist-db)
    ├── toolsets.yaml             ← Toolset registry (default, admin, ...)
    └── orders.yaml               ← Tool definitions for orders department
```

---

## Add a New Tool

1. Create or edit a department file under `tools/` (e.g. `tools/customers.yaml`)
2. Define the tool:
```yaml
tools:
  tool_name:
    kind: postgres-sql
    source: olist-db
    description: ...
    parameters:
      - name: param1
        type: string
        description: ...
    statement: |
      SELECT ... WHERE col = $1
```
3. Register the tool in `tools/toolsets.yaml`
4. Toolbox auto-reloads within 3 seconds (poll-interval)

---

## Add a New Toolset

Edit `tools/toolsets.yaml`:
```yaml
toolsets:
  default:
    - get_orders_by_date
  admin:
    - get_orders_by_date
  marketing:              # new toolset
    - get_orders_by_date
    - get_customers       # new tool
```

Point Claude Desktop to: `http://localhost:5000/mcp/marketing`
