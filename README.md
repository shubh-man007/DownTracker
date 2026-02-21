# DownTracker

Tracks incidents and status updates from the [OpenAI Status Page](https://status.openai.com/) and surfaces new, updated, and resolved events.

**Live demo:** [https://downtracker.onrender.com/](https://downtracker.onrender.com/)

---

## Approach

Instead of polling the feed by repeatedly downloading the full RSS content or manually refreshing the page, this project uses **conditional GET with ETag** for efficient updates.

### How it works

1. **Conditional GET (ETag):**  
   Each request includes the `If-None-Match` header with the last known ETag. If the feed has not changed, the server responds with `304 Not Modified` and no body. This avoids transferring the full XML when nothing has changed.

2. **State persistence:**  
   The last seen feed state (incidents keyed by GUID) and ETag are stored in `state.json`. On each run, the current feed is compared against this state.

3. **Change detection:**  
   Only when a `200 OK` and new content are received, the feed is parsed and compared to the stored state. Changes are classified as new incidents, status updates, or resolved incidents.

4. **Bandwidth and scalability:**  
   For a 60-second poll interval, most requests return `304` with no payload. This keeps bandwidth and processing low.
---

## Project Structure

```
Bolna/
├── app.py          # FastAPI server (HTML + JSON API)
├── main.py         # Poller loop (CLI entry point)
├── utils/
│   ├── fetch.py    # HTTP fetch with conditional GET
│   ├── parse.py    # RSS parsing and state comparison
│   └── state.py    # JSON state load/save
├── state.json      # Persisted feed state (generated)
└── requirements.txt
```

---

## Local Setup

```bash
pip install -r requirements.txt
```

**CLI (console output only):**
```bash
python main.py
```

**Web server (HTML + API):**
```bash
uvicorn app:app --reload --port 8000
```

Then open http://localhost:8000

---

## API Endpoints

| Endpoint        | Description                    |
|----------------|--------------------------------|
| `GET /`        | HTML page listing incidents    |
| `GET /api/status` | JSON feed of current state |
