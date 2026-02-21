import asyncio
import logging
import aiohttp
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def fetchXML(
    session: aiohttp.ClientSession,
    url: str,
    etag: Optional[str] = None,
    max_retries: int = 3,
) -> Tuple[Optional[str], Optional[str]]:

    headers = {}
    if etag:
        headers["If-None-Match"] = etag

    for attempt in range(max_retries):
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:

                if resp.status == 304:
                    return None, etag

                resp.raise_for_status()
                new_etag = resp.headers.get("ETag")
                return await resp.text(), new_etag

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            wait = 2 ** attempt
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1,
                max_retries,
                e,
                wait,
            )
            await asyncio.sleep(wait)

    logger.error("All %d attempts failed for %s", max_retries, url)
    return None, etag