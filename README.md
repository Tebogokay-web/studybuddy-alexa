# StudyBuddy for Alexa+ (simulated)

A voice-first study planner built for the **Amazon Developer Hackathon – Alexa+ track (simulated experience path)**.
Students speak or type to an Alexa+-style assistant to add assignments, check what's due, mark work done and get an automatic weekly study plan.

## How it works
- `index.html` is the whole app (HTML/CSS/JavaScript, no dependencies, no build step).
- **Speech in/out:** the browser's Web Speech API (mic button and spoken replies; works best in Chrome/Edge). Typing works everywhere.
- **Intent parsing:** a small rule-based parser turns an utterance into a tool call.
- **Tools:** `add_task`, `list_tasks`, `complete_task`, `delete_task`, `plan_week`. These are the same actions an MCP server would expose to Alexa+; the right-hand "Agent tool calls" panel shows each call live.
- **Storage:** assignments are kept in the browser's localStorage.

## Run it
Open `index.html` in a browser, or run `python -m http.server 8000` and visit http://localhost:8000.

Try: "add Python quiz due Friday" · "what's due" · "plan my week" · "finished Python quiz"

## Hackathon entry
- Track: Alexa+ (simulated experience path)
- Mini challenge: Open Source (MIT licence, see `LICENSE`)

## Licence
MIT © 2026 Tebogo Boy Molaudzi
