#!/usr/bin/env python3
"""
Tiny MCP client that talks to server.py over Streamable HTTP and prints every step.
Great for showing the server working in a terminal.

Usage:  python demo_client.py [http://localhost:8000/mcp]
"""

import json
import sys
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
session_id = None
next_id = 0


def send(method, params=None, notification=False):
    """POST one JSON-RPC message and return the parsed result (None for notifications)."""
    global session_id, next_id
    message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notification:
        next_id += 1
        message["id"] = next_id

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    request = urllib.request.Request(URL, json.dumps(message).encode(), headers, method="POST")
    with urllib.request.urlopen(request) as response:
        if method == "initialize":
            session_id = response.headers.get("Mcp-Session-Id")
        body = response.read()
    if notification:
        return None
    reply = json.loads(body)
    if "error" in reply:
        raise RuntimeError(reply["error"]["message"])
    return reply["result"]


def call(name, **arguments):
    print(f"\n>>> tools/call {name} {json.dumps(arguments)}")
    result = send("tools/call", {"name": name, "arguments": arguments})
    print(result["content"][0]["text"])


init = send("initialize", {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {"name": "demo-client", "version": "1.0.0"},
})
print(f"Connected to {init['serverInfo']['title']} (protocol {init['protocolVersion']}, session {session_id[:8]}...)")
send("notifications/initialized", notification=True)

tools = send("tools/list")["tools"]
print("Tools:", ", ".join(tool["name"] for tool in tools))

call("add_task", title="Python quiz", due="friday")
call("add_task", title="C++ assignment", due="in 3 days")
call("list_tasks")
call("plan_week")
call("complete_task", query="python")
call("list_tasks")
