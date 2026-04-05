"""
Dev-flow SQL query runner.
Usage: python query_db.py "<SQL>" [connection_name]
"""

import sys
import configparser
from pathlib import Path
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# 1. Load sys args
# ---------------------------------------------------------------------------
def _parse_args():
    if len(sys.argv) < 2:
        print("Usage: query_db.py <query> [connection_name]", file=sys.stderr)
        sys.exit(1)
    query = sys.argv[1]
    conn_name = sys.argv[2] if len(sys.argv) > 2 else "default"
    return query, conn_name


# ---------------------------------------------------------------------------
# 2. Load connections.conf
# ---------------------------------------------------------------------------
def _load_connections(conf_path: Path | None = None) -> configparser.ConfigParser:
    if conf_path is None:
        conf_path = Path(__file__).parent / "connections.conf"
    cfg = configparser.ConfigParser()
    read = cfg.read(conf_path)
    if not read:
        print(f"connections.conf not found at {conf_path}", file=sys.stderr)
        sys.exit(1)
    return cfg


# ---------------------------------------------------------------------------
# 3. Detect engine type from URL
# ---------------------------------------------------------------------------
def _detect_engine_type(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower().split("+")[0]  # strip existing driver suffix
    host = parsed.hostname or ""

    if "supabase.co" in host:
        return "supabase"
    if scheme in ("postgresql", "postgres"):
        return "postgres"
    if scheme == "mysql":
        return "mysql"

    raise ValueError(f"Unsupported scheme '{parsed.scheme}' in connection URL")


# ---------------------------------------------------------------------------
# 4. Resolve SQLAlchemy URL (inject driver)
# ---------------------------------------------------------------------------
def _resolve_url(url: str, engine_type: str) -> str:
    parsed = urlparse(url)
    bare_scheme = parsed.scheme.split("+")[0]  # strip any existing driver

    driver_map = {
        "postgres": "postgresql+psycopg2",
        "supabase": "postgresql+psycopg2",
        "mysql":    "mysql+pymysql",
    }
    new_scheme = driver_map.get(engine_type, bare_scheme)
    return url.replace(parsed.scheme, new_scheme, 1)


# ---------------------------------------------------------------------------
# 5. Build SQLAlchemy engine
# ---------------------------------------------------------------------------
def _build_engine(engine_type: str, sa_url: str):
    from sqlalchemy import create_engine

    connect_args = {}
    if engine_type == "supabase":
        connect_args["sslmode"] = "require"

    return create_engine(sa_url, connect_args=connect_args)


# ---------------------------------------------------------------------------
# 6 & 7. Connect and execute
# ---------------------------------------------------------------------------
def _execute(engine, query: str):
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text(query))
        if result.returns_rows:
            columns = list(result.keys())
            rows = result.fetchall()
            return columns, rows
        conn.commit()
        return [], []


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def _print_table(columns: list, rows: list):
    if not columns:
        print("Query executed successfully (no rows returned).")
        return

    widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val) if val is not None else "NULL"))

    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    sep    = "-+-".join("-" * w for w in widths)
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join((str(v) if v is not None else "NULL").ljust(widths[i]) for i, v in enumerate(row)))
    print(f"\n({len(rows)} rows)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    query, conn_name = _parse_args()

    cfg = _load_connections()
    if conn_name not in cfg:
        print(f"Connection '{conn_name}' not found in connections.conf", file=sys.stderr)
        sys.exit(1)

    raw_url     = cfg[conn_name]["url"]
    engine_type = _detect_engine_type(raw_url)   # step 3
    sa_url      = _resolve_url(raw_url, engine_type)  # step 4
    engine      = _build_engine(engine_type, sa_url)   # step 5
    columns, rows = _execute(engine, query)             # steps 6 & 7
    _print_table(columns, rows)


if __name__ == "__main__":
    main()
