# Create Department Toolset Skill

Create a new MCP toolset for a department by exploring the database schema, generating tool definitions, registering in toolsets.yaml, and validating via the toolbox API.

## Usage

```
/create-department-toolset <dept_name> [db_connection] [schema]
```

**Examples:**
```
/create-department-toolset marketing
/create-department-toolset hr ftask ftask
/create-department-toolset finance supabase public
```

**Arguments:**
- `dept_name` — department name (used in file name and toolset key, e.g. `marketing` → `dept_marketing`)
- `db_connection` — connection name from `.claude/scripts/connections.conf` (default: `supabase`)
- `schema` — database schema to explore (default: `public`)

---

## Workflow

### Step 1 — Resolve arguments

Parse the arguments. Apply defaults:
- `db_connection` = `supabase` if omitted
- `schema` = `public` if omitted

Determine `source_name` from the connection:
- If `db_connection` contains `ftask` → source is `ftask-db` (mysql-sql tools, `?` params)
- Otherwise → source is `olist-db` (postgres-sql tools, `$1` params)

### Step 2 — Explore schema

Run these queries via `python .claude/scripts/query_db.py`:

**For MySQL (`ftask` connection):**
```bash
python .claude/scripts/query_db.py "SHOW TABLES FROM {schema}" {db_connection}
python .claude/scripts/query_db.py "DESCRIBE {schema}.{table}" {db_connection}   # for each table
```

**For PostgreSQL:**
```bash
python .claude/scripts/query_db.py "SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}' ORDER BY table_name" {db_connection}
python .claude/scripts/query_db.py "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}' ORDER BY ordinal_position" {db_connection}
```

Also sample a few rows to understand data values:
```bash
python .claude/scripts/query_db.py "SELECT DISTINCT {key_col} FROM {schema}.{table} LIMIT 20" {db_connection}
```

### Step 3 — Design tools

Based on the schema, design **3–6 tools** focused on **read-only analytics/performance queries**. Each tool should:
- Have a clear, actionable purpose (not just "get all rows")
- Use date range parameters (`date_from`, `date_to`) for time-series data
- Include a `limit` param for ranked/top-N queries
- Have a thorough `description` with all output fields documented

**Tool naming:** `{dept_name}_{verb}_{subject}` (e.g. `marketing_get_campaign_summary`)

**MySQL tools** use:
```yaml
kind: mysql-sql
source: ftask-db
# params use ? placeholders
statement: |
  SELECT ... WHERE DATE(col) >= ? AND DATE(col) <= ?
```

**PostgreSQL tools** use:
```yaml
kind: postgres-sql
source: olist-db
# params use $1, $2, $3 placeholders
statement: |
  SELECT ... WHERE col >= $1::date AND col < $2::date
```

### Step 4 — Write `tools/dept_{dept_name}.yaml`

Follow the format from `tools/dept_omt.yaml` or `tools/dept_admin.yaml` exactly.

Check if the file already exists — if so, ask the user before overwriting.

### Step 5 — Register in `tools/toolsets.yaml`

Read the current `toolsets.yaml`. Add a new toolset block:
```yaml
  dept_{dept_name}:
    - {tool_1}
    - {tool_2}
    ...
```

Do NOT create a duplicate key if `dept_{dept_name}` already exists — append missing tools instead.

### Step 6 — Wait for toolbox reload

The toolbox polls every 3 seconds. Wait 4 seconds after writing the files, then test.

```bash
sleep 4
```

### Step 7 — Test each tool via API

For **each tool**, call the invoke endpoint. Use minimal valid params (e.g. a date range with known data, limit=5).

**Get sample date range first (MySQL):**
```bash
python .claude/scripts/query_db.py "SELECT MIN(DATE(created_at)), MAX(DATE(created_at)) FROM {schema}.{main_table}" {db_connection}
```

**Test a tool:**
```bash
curl -s -X POST http://localhost:5000/api/tool/{tool_name}/invoke \
  -H "Content-Type: application/json" \
  -d '{"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD"}'
```

For tools with no params:
```bash
curl -s -X POST http://localhost:5000/api/tool/{tool_name}/invoke \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Step 8 — Report results

Print a summary table:

```
TOOLSET: dept_{dept_name}
Endpoint: http://localhost:5000/mcp/dept_{dept_name}

Tool                          Status   Sample output
--------------------------    ------   -------------
{tool_1}                      PASS     "{first row preview}"
{tool_2}                      PASS     "{first row preview}"
{tool_3}                      FAIL     "error message"
```

If any tool FAILs:
1. Read the error message
2. Fix the SQL (wrong column name, bad syntax, unsupported function)
3. Re-test that tool
4. Update the summary

---

## Key Rules

- **Read-only only** — never generate INSERT/UPDATE/DELETE statements in tool definitions
- **MySQL params** = `?` positional; **PostgreSQL params** = `$1`, `$2`, `$3`
- **Always test** — do not skip Step 7, even if the YAML looks correct
- **Docker restart not needed** — yaml hot-reload works; only restart if new env vars were added to `.env`
- **No duplicate toolset keys** — YAML silently uses the last one, causing confusion
