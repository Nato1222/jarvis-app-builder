# JarvisOne Tools

This folder contains small utilities agents can call during planning/execution.

File Search API (FastAPI router)
- Module: `JarvisOne.tools.file_search`
- Mounted under `/api/tools`

Endpoints
- POST `/api/tools/search` { "query": "filename or keyword" } -> ["relative/path"]
- POST `/api/tools/read` { "path": "relative/path/to/file" } -> "first 1000 chars"

Notes
- Only reads regular files within the project root.
- Hidden/system and blocked folders are skipped: .git, node_modules, __pycache__, .venv
- Content search scans first ~200KB of each file for speed.
