---
name: Google MCP Toolbox Gotchas
description: Non-obvious behaviors of Google MCP Toolbox for Databases v0.31+
type: feedback
---

Key findings discovered through debugging:

1. **Default bind address is 127.0.0.1** — must add `--address=0.0.0.0` for other containers to reach it.
   **Why:** Without this, bridge/other containers get "connection refused" even on same Docker network.

2. **SQL parameters use `$1`, `$2` (positional), NOT `{{.param}}`** — toolbox renders Go template first, THEN binds params as prepared statement. Using `{{.param}}` in SQL causes `<no value>` because both steps run and conflict.
   **How to apply:** Always use `$1`, `$2` for value binding in SQL statements. `{{.param}}` is only for dynamic SQL structure (table names, conditionals).

3. **`--config-folder` is flat only** — does NOT recurse into subdirectories. All tool yaml files must be in the root of the folder.
   **How to apply:** Keep `tools/` flat: `source.yaml`, `toolsets.yaml`, `orders.yaml`, `customers.yaml`, etc.

4. **Hot-reload doesn't work on Windows** — NTFS → WSL2 → Docker breaks inotify. Use `--poll-interval=3` as workaround.

5. **Toolset routing:** `GET /mcp` = default toolset, `GET /mcp/{toolset}` = specific toolset. Also supports `?toolset=name` query param.

6. **Supabase direct connection resolves IPv6** — Docker containers have no IPv6 route. Use Supabase connection pooler (`*.pooler.supabase.com`) which resolves to IPv4.
