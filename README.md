# StudyBuddy for Alexa+ (MCP server)

A self-hosted **MCP server** (Streamable HTTP, spec revision **2025-11-25**) that turns Alexa+ into a study planner, plus a voice-enabled web app that talks to it.
Built for the **Amazon Developer Hackathon – Alexa+ track**.

Ask for things like "add Python quiz due Friday", "what's due", "plan my week" or "finished Python quiz".

## Project structure
| File | Purpose |
|------|---------|
| `server.py` | The MCP server (Python standard library only, no installs). Also serves the web app. |
| `index.html` | Voice/chat web app that acts as an MCP client of `server.py` (falls back to a local copy of the tools if the server isn't running) |
| `demo_client.py` | Small command-line MCP client that shows the full protocol flow in a terminal |
| `LICENSE` | MIT licence |

## MCP details
- **Endpoint:** `POST /mcp` (single endpoint, JSON responses). `GET /mcp` returns 405 because the server doesn't open a server-initiated SSE stream.
- **Handshake:** `initialize` → `notifications/initialized` → `tools/list` / `tools/call`, with `Mcp-Session-Id` and `MCP-Protocol-Version` headers.
- **Tools:** `add_task`, `list_tasks`, `complete_task`, `delete_task`, `plan_week`. Results include text `content` plus `structuredContent`, and tool problems are returned as `isError: true`.
- **Security:** the `Origin` header is validated (localhost only by default) and the server binds to `127.0.0.1`.
- **Storage:** tasks are saved to `tasks.json`.

## Run it
Requires Python 3.9+. No dependencies.

```bash
python server.py
```

- Open http://localhost:8000 for the web app (the header shows "connected to MCP server").
- In a second terminal, run `python demo_client.py` to watch a client use the tools.
- Any MCP client can connect to `http://localhost:8000/mcp`. To use it from Alexa+, expose the server on a public HTTPS URL (for example with a tunnel) and register that URL as the MCP endpoint.

## Hackathon entry
- Track: Alexa+ (self-hosted MCP server, Streamable HTTP)
- Mini challenge: Open Source (MIT licence)

## Licence
MIT © 2026 Tebogo Boy Molaudzi
