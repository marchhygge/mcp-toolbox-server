# System Architecture Overview

## High-Level Architecture

```mermaid
graph TB
    subgraph Client["Claude Desktop (Client)"]
        CD[Claude Desktop]
        MR1["mcp-remote\ntoolbox-default"]
        MR2["mcp-remote\ntoolbox-admin"]
        CD --> MR1
        CD --> MR2
    end

    subgraph Server["AWS EC2 (Production)"]
        TB["MCP Toolbox\nGoogle genai-toolbox\nDocker :5000"]
        YAML["/tools/*.yaml\nTool Definitions"]
        TB -- "polls every 3s" --> YAML
    end

    subgraph Databases["Databases"]
        ODB[("olist-db\nPostgreSQL\nSupabase")]
        FDB[("ftask-db\nMySQL")]
    end

    MR1 -- "HTTP/SSE /mcp" --> TB
    MR2 -- "HTTP/SSE /mcp/admin" --> TB
    TB -- "postgres-sql tools" --> ODB
    TB -- "mysql-sql tools" --> FDB
```

---

## Toolset → Tool → Database Mapping

```mermaid
graph LR
    TB["MCP Toolbox\n:5000"] --> EP1["/mcp\ndefault"]
    TB --> EP2["/mcp/omt\nomt"]
    TB --> EP3["/mcp/admin\nadmin"]

    subgraph Default["default toolset"]
        EP1 --> D1["get_orders_by_date"]
        EP1 --> D2["omt_get_revenue_summary"]
    end

    subgraph OMT["omt toolset — Olist Marketplace Team"]
        EP2 --> O1["omt_get_revenue_summary"]
        EP2 --> O2["omt_get_order_status_breakdown"]
        EP2 --> O3["omt_get_top_sellers"]
        EP2 --> O4["omt_get_top_categories"]
        EP2 --> O5["omt_get_customer_satisfaction"]
        EP2 --> O6["omt_get_delivery_performance"]
        EP2 --> O7["omt_get_payment_methods"]
    end

    subgraph Admin["admin toolset — Administration"]
        EP3 --> A1["admin_get_user_summary"]
        EP3 --> A2["admin_get_ticket_performance"]
        EP3 --> A3["admin_get_staff_ticket_workload"]
        EP3 --> A4["admin_get_dashboard_usage_summary"]
        EP3 --> A5["admin_get_system_activity_summary"]
    end

    ODB[("olist-db\nPostgreSQL")]
    FDB[("ftask-db\nMySQL")]

    D1 --> ODB
    D2 --> ODB
    O1 --> ODB
    O2 --> ODB
    O3 --> ODB
    O4 --> ODB
    O5 --> ODB
    O6 --> ODB
    O7 --> ODB
    A1 --> FDB
    A2 --> FDB
    A3 --> FDB
    A4 --> FDB
    A5 --> FDB
```

---

## CI/CD Deployment Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub (main branch)
    participant GA as GitHub Actions
    participant EC2 as AWS EC2
    participant Docker as Docker Compose
    participant CD as Claude Desktop

    Dev->>GH: git push origin main
    GH->>GA: trigger deploy.yml
    GA->>EC2: SSH (appleboy/ssh-action)
    EC2->>EC2: git pull origin main
    EC2->>Docker: docker compose up -d --pull always
    Docker->>Docker: pull latest toolbox image
    Docker-->>EC2: toolbox running on :5000
    CD->>EC2: connect via mcp-remote
```

---

## Data Model

### olist-db — Supabase PostgreSQL

```mermaid
erDiagram
    fact_order {
        string order_id PK
        string order_status
        date order_date
        timestamp order_purchase_timestamp
        timestamp order_delivered_customer_date
        timestamp order_estimated_delivery_date
        float total_price
        float total_payment
        float avg_score
    }

    fact_order_item {
        string order_id FK
        string seller_id FK
        string product_id FK
        int order_item_id
        date order_date
        float total_price
        float total_freight_value
    }

    fact_order_review {
        string order_id FK
        date order_date
        float avg_score
        int total_reviews
    }

    fact_payment {
        string order_id FK
        string payment_type
        date order_date
        float total_payment_value
        int payment_installments
    }

    dim_user {
        string user_id PK
        string user_type
        string city
        string state
    }

    dim_product {
        string product_id PK
        string category_name
    }

    fact_order ||--o{ fact_order_item : "has items"
    fact_order ||--o| fact_order_review : "has review"
    fact_order ||--o{ fact_payment : "has payments"
    fact_order_item }o--|| dim_user : "sold by seller"
    fact_order_item }o--|| dim_product : "is product"
```

### ftask-db — MySQL

```mermaid
erDiagram
    department {
        int department_id PK
        string department_name
        string department_type
        int manager FK
        string status
    }

    User {
        int user_id PK
        string user_name
        string email
        string status
        int department_id FK
    }

    ticket {
        int ticket_id PK
        string type
        string status
        int assigned_staff FK
        timestamp created_at
    }

    dashboard {
        int dashboard_id PK
        string dashboard_name
        string category
    }

    dashboard_usage_logs {
        int log_id PK
        int user_id FK
        int dashboard_id FK
        timestamp accessed_at
        float duration
    }

    system_audit_logs {
        int log_id PK
        int user_id FK
        string target_entity
        string action
        timestamp timestamp
    }

    department ||--o{ User : "has members"
    department ||--|| User : "managed by"
    User ||--o{ ticket : "assigned to"
    User ||--o{ dashboard_usage_logs : "accessed by"
    dashboard ||--o{ dashboard_usage_logs : "tracked in"
    User ||--o{ system_audit_logs : "performed by"
```

---

## Components

### 1. Claude Desktop
The AI client. Connects to the MCP Toolbox via `mcp-remote` — an npm package that bridges MCP's SSE transport to Claude Desktop's stdio interface.

Each configured server in `claude_desktop_config.json` maps to one toolset endpoint:

| Config Key | Endpoint | Toolset |
|---|---|---|
| `toolbox-default` | `/mcp` | default |
| `toolbox-admin` | `/mcp/admin` | admin |

### 2. MCP Toolbox (Google genai-toolbox)
The core backend. Runs as a Docker container and:
- Reads YAML configs from the mounted `tools/` directory
- Exposes each tool as an MCP-compatible function
- Auto-reloads configs every 3 seconds (no restart needed)
- Provides a test UI at `/ui` and REST API at `/api/toolset/`

### 3. Databases

| Name | Engine | Host | Schema | Purpose |
|---|---|---|---|---|
| `olist-db` | PostgreSQL | Supabase | `centralize.*`, `public.*` | Olist e-commerce analytics |
| `ftask-db` | MySQL | self-hosted | `ftask.*` | Internal task management (FTask) |

---

## Tool Definition Format

Tools are defined in YAML under `tools/`. There are two kinds:

```yaml
tools:
  tool_name:
    kind: postgres-sql        # or mysql-sql
    source: olist-db          # references sources in source.yaml
    description: >
      Natural language description used by Claude to understand when/how to call this tool.
    parameters:
      - name: date_from
        type: string          # string | integer
        description: Start date (YYYY-MM-DD)
    statement: |
      SELECT ... WHERE col >= $1   -- postgres: $1, $2, ...
      -- or --
      SELECT ... WHERE col >= ?    -- mysql: positional ?
```

Parameter binding:
- **PostgreSQL** tools use `$1`, `$2`, `$3` positional placeholders
- **MySQL** tools use `?` positional placeholders

---

## Volume Mount Structure

```
tools/                          ← bind-mounted to /tools in container
├── .env                        ← DB credentials (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
├── source.yaml                 ← declares olist-db (postgres), ftask-db (mysql)
├── toolsets.yaml               ← maps toolset names → list of tool names
├── orders.yaml                 ← tool: get_orders_by_date
├── dept_omt.yaml               ← tools: omt_*  (7 tools)
└── dept_admin.yaml             ← tools: admin_* (5 tools)
```

---

## Configuration Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines the `toolbox` service, port mapping, volume, env |
| `tools/source.yaml` | DB connection definitions (host, port, db, credentials via env vars) |
| `tools/toolsets.yaml` | Toolset registry — maps names to tool lists |
| `tools/.env` | DB credentials loaded into the container at runtime |
| `claude_desktop_config.example.json` | Template for `%APPDATA%\Claude\claude_desktop_config.json` |
| `.github/workflows/deploy.yml` | CI/CD: auto-deploy to EC2 on push to `main` |

---

## Adding New Tools (Summary)

1. Create or edit a YAML file in `tools/` (e.g. `tools/dept_marketing.yaml`)
2. Define one or more tools with `kind`, `source`, `description`, `parameters`, `statement`
3. Register each tool name in `tools/toolsets.yaml` under an existing or new toolset
4. Toolbox picks up the change within 3 seconds — no restart needed
