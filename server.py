#!/usr/bin/env python3
"""
StudyBuddy MCP server
=====================
A self-hosted Model Context Protocol (MCP) server for study planning, built for the
Alexa+ track of the Amazon Developer Hackathon.

  * Transport:    Streamable HTTP (single endpoint: POST /mcp), spec revision 2025-11-25
  * Dependencies: none (Python 3.9+ standard library only)
  * Tools:        add_task, list_tasks, complete_task, delete_task, plan_week

Run:   python server.py          (then open http://localhost:8000 for the web app)
"""

import argparse
import json
import re
import threading
import uuid
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "tasks.json"
MCP_PATH = "/mcp"

LATEST_PROTOCOL = "2025-11-25"
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26")
SERVER_INFO = {"name": "studybuddy-mcp", "title": "StudyBuddy Study Planner", "version": "1.0.0"}

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SESSIONS = set()  # ids of active MCP sessions


# ----------------------------------------------------------------------
# Task storage (JSON file on disk)
# ----------------------------------------------------------------------

class ToolError(Exception):
    """A problem the model can read and fix (reported as isError: true)."""


class TaskStore:
    """Each task is {"title": str, "due": "YYYY-MM-DD" | None, "done": bool}."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.tasks = []
        if path.exists():
            try:
                self.tasks = json.loads(path.read_text())
            except (OSError, ValueError):
                self.tasks = []

    def save(self):
        self.path.write_text(json.dumps(self.tasks, indent=2))

    def find(self, query):
        query = (query or "").strip().lower()
        if not query:
            raise ToolError("Please say which assignment you mean.")
        for task in self.tasks:
            if query in task["title"].lower():
                return task
        raise ToolError(f'I couldn\'t find "{query}".')


STORE = TaskStore(DATA_FILE)


# ----------------------------------------------------------------------
# Date helpers
# ----------------------------------------------------------------------

def parse_due(value):
    """Accepts YYYY-MM-DD, today, tomorrow, 'in N days' or a weekday name."""
    if not value:
        return None
    text = str(value).strip().lower()
    today = date.today()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            date.fromisoformat(text)
        except ValueError:
            raise ToolError(f"{text} is not a real date.")
        return text
    if text == "today":
        return today.isoformat()
    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    match = re.fullmatch(r"in (\d+) days?", text)
    if match:
        return (today + timedelta(days=int(match.group(1)))).isoformat()
    if text in WEEKDAYS:
        days_ahead = (WEEKDAYS.index(text) - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_ahead)).isoformat()

    raise ToolError('Use a date like "2026-10-30", "friday", "tomorrow" or "in 3 days".')


def pretty(iso_date):
    return date.fromisoformat(iso_date).strftime("%A %d %b")


# ----------------------------------------------------------------------
# Tool implementations: each takes an arguments dict and returns text
# ----------------------------------------------------------------------

def add_task(args):
    title = str(args.get("title") or "").strip()
    if not title:
        raise ToolError("A title is required.")
    due = parse_due(args.get("due"))
    STORE.tasks.append({"title": title[:1].upper() + title[1:], "due": due, "done": False})
    STORE.save()
    return f'Done. I added "{STORE.tasks[-1]["title"]}"' + (f", due {pretty(due)}." if due else ".")


def list_tasks(args):
    pending = sorted((t for t in STORE.tasks if not t["done"]), key=lambda t: t["due"] or "9999")
    if not pending:
        return "You have nothing pending. Nice work!"
    lines = [f"• {t['title']}" + (f" – {pretty(t['due'])}" if t["due"] else "") for t in pending]
    return f"You have {len(pending)} pending:\n" + "\n".join(lines)


def complete_task(args):
    task = STORE.find(args.get("query"))
    task["done"] = True
    STORE.save()
    return f'Great job! "{task["title"]}" is marked done.'


def delete_task(args):
    task = STORE.find(args.get("query"))
    STORE.tasks.remove(task)
    STORE.save()
    return f'Removed "{task["title"]}".'


def plan_week(args):
    """Schedules a one-hour study session the day before each deadline."""
    upcoming = sorted((t for t in STORE.tasks if not t["done"] and t["due"]), key=lambda t: t["due"])
    if not upcoming:
        return "Add some assignments with due dates and I'll plan your week."
    today = date.today().isoformat()
    lines = []
    for task in upcoming:
        day_before = (date.fromisoformat(task["due"]) - timedelta(days=1)).isoformat()
        session_day = max(day_before, today)
        overdue = " ⚠ overdue!" if task["due"] < today else ""
        lines.append(f'• {pretty(session_day)}: study "{task["title"]}"{overdue}')
    return "Here's your study plan (1 hour each):\n" + "\n".join(lines)


TOOL_HANDLERS = {
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "delete_task": delete_task,
    "plan_week": plan_week,
}

TOOLS = [
    {
        "name": "add_task",
        "title": "Add assignment",
        "description": "Add an assignment or study task, optionally with a due date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Name of the assignment, e.g. 'Python quiz'"},
                "due": {"type": "string", "description": "Due date: YYYY-MM-DD, a weekday, 'tomorrow' or 'in 3 days'"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "title": "List pending assignments",
        "description": "List every unfinished assignment, earliest deadline first.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "complete_task",
        "title": "Mark assignment done",
        "description": "Mark an assignment as finished. Matches part of the title.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Part of the assignment title"}},
            "required": ["query"],
        },
    },
    {
        "name": "delete_task",
        "title": "Delete assignment",
        "description": "Remove an assignment. Matches part of the title.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Part of the assignment title"}},
            "required": ["query"],
        },
        "annotations": {"destructiveHint": True},
    },
    {
        "name": "plan_week",
        "title": "Plan my week",
        "description": "Build a study plan: a one-hour session the day before each deadline.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
]


# ----------------------------------------------------------------------
# JSON-RPC / MCP message handling
# ----------------------------------------------------------------------

def rpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_initialize(req_id, params):
    requested = params.get("protocolVersion")
    version = requested if requested in SUPPORTED_PROTOCOLS else LATEST_PROTOCOL
    session_id = uuid.uuid4().hex
    SESSIONS.add(session_id)
    result = {
        "protocolVersion": version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": SERVER_INFO,
        "instructions": "Study planner. Add assignments, list what's due, mark them done, or plan the week.",
    }
    return rpc_result(req_id, result), session_id


def handle_tool_call(req_id, params):
    name = params.get("name")
    args = params.get("arguments") or {}
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return rpc_error(req_id, -32602, f"Unknown tool: {name}")
    if not isinstance(args, dict):
        return rpc_error(req_id, -32602, "arguments must be an object")

    with STORE.lock:
        try:
            text, is_error = handler(args), False
        except ToolError as exc:
            text, is_error = str(exc), True
        snapshot = json.loads(json.dumps(STORE.tasks))

    return rpc_result(req_id, {
        "content": [{"type": "text", "text": text}],
        "structuredContent": {"tasks": snapshot},  # lets the web app redraw its list
        "isError": is_error,
    })


def handle_request(req_id, method, params):
    if method == "ping":
        return rpc_result(req_id, {})
    if method == "tools/list":
        return rpc_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        return handle_tool_call(req_id, params)
    return rpc_error(req_id, -32601, f"Method not found: {method}")


# ----------------------------------------------------------------------
# HTTP layer (Streamable HTTP transport + static hosting of the web app)
# ----------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "StudyBuddyMCP/1.0"
    extra_origins = set()

    # --- helpers ---

    def origin_allowed(self):
        """Blocks DNS-rebinding style attacks: only local pages may call the server."""
        origin = self.headers.get("Origin")
        if origin is None or origin in self.extra_origins:
            return True
        return urlparse(origin).hostname in ("localhost", "127.0.0.1", "::1")

    def send_body(self, status, body=None, content_type="application/json", headers=None):
        if body is None:
            payload = b""
        elif isinstance(body, bytes):
            payload = body
        else:
            payload = json.dumps(body).encode("utf-8")

        self.send_response(status)
        origin = self.headers.get("Origin")
        if origin and self.origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")
            self.send_header("Vary", "Origin")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        if payload:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_rpc_error(self, status, code, message):
        self.send_body(status, rpc_error(None, code, message))

    # --- HTTP verbs ---

    def do_OPTIONS(self):  # CORS preflight
        if not self.origin_allowed():
            return self.send_body(403)
        self.send_body(204, headers={
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id, MCP-Protocol-Version",
        })

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = BASE_DIR / "index.html"
            if page.exists():
                return self.send_body(200, page.read_bytes(), "text/html; charset=utf-8")
            return self.send_body(404)
        if path == MCP_PATH:  # this server does not offer a server-to-client SSE stream
            return self.send_body(405, headers={"Allow": "POST, DELETE, OPTIONS"})
        self.send_body(404)

    def do_DELETE(self):  # lets a client end its session
        if urlparse(self.path).path != MCP_PATH:
            return self.send_body(404)
        if not self.origin_allowed():
            return self.send_body(403)
        SESSIONS.discard(self.headers.get("Mcp-Session-Id"))
        self.send_body(204)

    def do_POST(self):
        if urlparse(self.path).path != MCP_PATH:
            return self.send_body(404)
        if not self.origin_allowed():
            return self.send_rpc_error(403, -32600, "Origin not allowed")

        version = self.headers.get("MCP-Protocol-Version")
        if version and version not in SUPPORTED_PROTOCOLS:
            return self.send_rpc_error(400, -32600, f"Unsupported MCP-Protocol-Version: {version}")

        length = int(self.headers.get("Content-Length") or 0)
        if length > 1_000_000:
            return self.send_rpc_error(413, -32600, "Request too large")
        try:
            message = json.loads(self.rfile.read(length) or b"null")
        except ValueError:
            return self.send_rpc_error(400, -32700, "Parse error")
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self.send_rpc_error(400, -32600, "Send a single JSON-RPC 2.0 message")

        # Notifications and responses from the client get 202 Accepted with no body.
        method = message.get("method")
        if method is None or "id" not in message:
            return self.send_body(202)

        req_id = message["id"]
        params = message.get("params") or {}

        if method == "initialize":
            response, session_id = handle_initialize(req_id, params)
            return self.send_body(200, response, headers={"Mcp-Session-Id": session_id})

        session_id = self.headers.get("Mcp-Session-Id")
        if session_id and session_id not in SESSIONS:
            return self.send_rpc_error(404, -32600, "Unknown session, please initialize again")

        self.send_body(200, handle_request(req_id, method, params))

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


def main():
    parser = argparse.ArgumentParser(description="StudyBuddy MCP server (Streamable HTTP)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--allow-origin", action="append", default=[],
                        help="extra browser origin allowed to call the server (repeatable)")
    args = parser.parse_args()

    Handler.extra_origins = set(args.allow_origin)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"StudyBuddy MCP server  ->  http://{args.host}:{args.port}{MCP_PATH}  (spec {LATEST_PROTOCOL})")
    print(f"Web app                ->  http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")


if __name__ == "__main__":
    main()
