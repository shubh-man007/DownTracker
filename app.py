import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from main import runPoller
from utils.state import loadState

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    poller_task = asyncio.create_task(runPoller())
    logger.info("Background poller started")
    yield
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OpenAI Status Tracker",
    lifespan=lifespan,
)


def _formatProduct(item: Dict[str, Any]) -> str:
    components = item.get("Components") or []
    if components:
        return "OpenAI API - " + ", ".join(components)
    return item.get("Title") or "OpenAI"


@app.get("/", response_class=HTMLResponse)
async def root():
    state = loadState()
    if state is None:
        return _htmlPage(
            title="OpenAI Status Tracker",
            message="No data yet.",
            items=[],
            lastBuildDate=None,
        )

    feed = state.get("feed_state", {})
    items = list(feed.get("Items", {}).items())
    items.sort(key=lambda x: x[1].get("PubDate") or "", reverse=True)

    return _htmlPage(
        title="OpenAI Status Tracker",
        message=f"Tracking {feed.get('ItemCount', 0)} incidents. Feed updates every 60s.",
        items=items,
        lastBuildDate=feed.get("LastBuildDate"),
    )


@app.get("/api/status")
async def apiStatus():
    state = loadState()
    if state is None:
        return JSONResponse(
            content={"status": "initializing", "feed_state": None},
            status_code=200,
        )
    return state


def _htmlPage(
    title: str,
    message: str,
    items: list,
    lastBuildDate: Optional[str],
) -> str:
    rows = []
    for guid, data in items[:50]:
        product = _formatProduct(data)
        status = data.get("Status") or "—"
        pub_date = data.get("PubDate") or "—"
        rows.append(
            f"""
            <tr>
                <td>{product}</td>
                <td><span class="status">{status}</span></td>
                <td class="muted">{pub_date}</td>
                <td><a href="{guid}" target="_blank" rel="noopener">View</a></td>
            </tr>
            """
        )

    table_body = "\n".join(rows) if rows else '<tr><td colspan="4" class="muted">No incidents</td></tr>'
    last_update = f"<p class='muted'>Feed last built: {lastBuildDate}</p>" if lastBuildDate else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{ --bg: #0f0f12; --fg: #e4e4e7; --muted: #71717a; --accent: #3b82f6; --card: #18181b; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--fg); min-height: 100vh; padding: 2rem; line-height: 1.6; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        .muted {{ color: var(--muted); font-size: 0.875rem; }}
        .status {{ display: inline-block; padding: 0.2em 0.5em; border-radius: 4px; font-size: 0.8rem; font-weight: 500; }}
        .status:not(:empty) {{ background: var(--card); color: var(--accent); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; background: var(--card); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }}
        th {{ background: rgba(0,0,0,0.2); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        tr:last-child td {{ border-bottom: none; }}
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="muted">{message}</p>
    {last_update}
    <table>
        <thead>
            <tr><th>Product / Incident</th><th>Status</th><th>Published</th><th>Link</th></tr>
        </thead>
        <tbody>
        {table_body}
        </tbody>
    </table>
</body>
</html>"""
