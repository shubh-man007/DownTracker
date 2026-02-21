import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import Any, Dict, Optional

from utils.parse import parseXML, GUIDHash, compareState
from utils.fetch import fetchXML
from utils.state import loadState, saveState

FEED_URL = "https://status.openai.com/feed.rss"
POLL_INTERVAL = 60

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _formatProduct(item: Dict[str, Any]) -> str:
    components = item.get("Components") or []
    if components:
        return "OpenAI API - " + ", ".join(components)
    return item.get("Title") or "OpenAI"


def logChanges(changes: Dict[str, Any]) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in changes["new"]:
        product = _formatProduct(item)
        status = item.get("Status") or "No status"
        logger.info("[%s] Product: %s\nStatus: %s", ts, product, status)

    for item in changes["updated"]:
        product = _formatProduct(item)
        status = f"{item.get('OldStatus') or 'Unknown'} → {item.get('NewStatus') or 'Unknown'}"
        logger.info("[%s] Product: %s\nStatus: %s", ts, product, status)

    for item in changes["resolved"]:
        product = _formatProduct(item)
        status = item.get("NewStatus") or item.get("Status") or "Resolved"
        logger.info("[%s] Product: %s\nStatus: %s", ts, product, status)


async def check(
    session: aiohttp.ClientSession,
    old_state: Optional[Dict],
    etag: Optional[str],
) -> tuple[Optional[Dict], Optional[str]]:
    xml_str, new_etag = await fetchXML(session, FEED_URL, etag=etag)

    if xml_str is None:
        return old_state, etag

    raw = parseXML(xml_str, item_tags=["title", "guid", "pubDate", "description"])
    new_state = GUIDHash(raw)
    changes = compareState(old_state, new_state)

    if any(changes[k] for k in ("new", "updated", "resolved")):
        logChanges(changes)
    else:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("[%s] No new incidents.", ts)

    return new_state, new_etag

async def runPoller():
    persisted = loadState()

    async with aiohttp.ClientSession() as session:
        if persisted is None:
            logger.info("Initializing state from feed")
            xml_str, etag = await fetchXML(session, FEED_URL)
            raw = parseXML(xml_str, item_tags=["title", "guid", "pubDate", "description"])
            feed_state = GUIDHash(raw)
            persisted = {"feed_state": feed_state, "etag": etag}
            saveState(persisted)
            logger.info("State initialized (%d incidents)", feed_state["ItemCount"])
        else:
            logger.info(
                "State loaded (%d incidents)",
                persisted["feed_state"]["ItemCount"]
            )

        while True:
            await asyncio.sleep(POLL_INTERVAL)
            new_state, new_etag = await check(
                session,
                old_state=persisted["feed_state"],
                etag=persisted["etag"],
            )
            persisted = {"feed_state": new_state, "etag": new_etag}
            saveState(persisted)


if __name__ == "__main__":
    asyncio.run(runPoller())