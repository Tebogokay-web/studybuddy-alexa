# StudyBuddy for Alexa+ (simulated)

A voice-first study planner built for the **Amazon Developer Hackathon – Alexa+ track (simulated experience path)**.
Students speak or type to an Alexa+-style assistant to add assignments, check what's due, mark work done and get an automatic weekly study plan.

## Project structure
| File | Purpose |
|------|---------|
| `index.html` | The whole app: layout, styling and logic in one file (CSS and JavaScript are in clearly labelled sections) |
| `LICENSE` | MIT licence |

## How it works
1. **Speech in/out:** the browser's Web Speech API (mic button and spoken replies; best in Chrome or Edge). Typing works everywhere.
2. **Intent parsing:** `understand()` in `index.html` turns a sentence into a tool call using simple rules.
3. **Tools:** `add_task`, `list_tasks`, `complete_task`, `delete_task`, `plan_week`. These are the actions an MCP server would expose to Alexa+. The "Agent tool calls" panel shows each call live.
4. **Storage:** assignments are kept in the browser's localStorage.

No dependencies and no build step.

## Run it
Open `index.html` in a browser, or run `python -m http.server 8000` and visit http://localhost:8000.

Try: "add Python quiz due Friday" · "what's due" · "plan my week" · "finished Python quiz"

## Hackathon entry
- Track: Alexa+ (simulated experience path)
- Mini challenge: Open Source (MIT licence)

## Licence
MIT © 2026 Tebogo Boy Molaudzi
