# 06 — C4 Container

```mermaid
C4Container
    title Containers - saas-catalog-api
    System_Ext(solo, "Solo Web BFF", "Next.js route /api/[service]/[...path]")
    Person(agent, "Owner agent")
    System_Boundary(repo, "platform-saas-catalog-api") {
        Container(http, "HTTP API", "Python 3.12, http.server ThreadingHTTPServer", "server.py on Railway, port PORT or 3490")
        ContainerDb(snap, "Catalog snapshot", "JSON file in image", "/app/data/free-saas-master-catalog-2026.json")
        Container(mcp, "saas-catalog-mcp", "Python, mcp + httpx, stdio", "Runs on the owner machine, not in the image")
        Container(val, "validate_catalog.py", "Python CLI", "Shape check of the snapshot")
    }
    System_Ext(sentry, "Sentry")
    System_Ext(files, "Owner key files", "~/.config/solo-web and ~/.config/empire-platform/client.env")
    Rel(solo, http, "GET /api/v1/saas", "HTTPS + Bearer JWT")
    Rel(agent, mcp, "MCP tool calls", "stdio")
    Rel(mcp, files, "Reads signing key and owner subject, mode 600")
    Rel(mcp, http, "GET /api/v1/saas", "HTTPS + Bearer JWT 60 s")
    Rel(http, snap, "Reads, cached by mtime")
    Rel(val, snap, "Validates")
    Rel(http, sentry, "capture on 500", "HTTPS")
```

Docker image มีแค่ `server.py`, `_sentry.py`, `pyproject.toml`, `uv.lock`, `vendor/service-auth` และไฟล์ snapshot (ไม่มี `saas_catalog_mcp.py` แม้จะอยู่ใน `py-modules`, ไม่มี optional `mcp` extra เพราะ `uv sync --no-dev` ไม่ใส่ extras)

Sources: `Dockerfile`, `pyproject.toml`, `server.py`, `saas_catalog_mcp.py`, `scripts/validate_catalog.py`, `_sentry.py`, `.mcp.json`
