import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def parseXML(xml_str: str, item_tags: List[str]) -> Dict:
    root = ET.fromstring(xml_str)
    channel = root.find("channel")

    if channel is None:
        return {"LastBuildDate": None, "ItemCount": 0, "Items": []}

    lastBuildDate = channel.find("lastBuildDate")
    last_build = (
        lastBuildDate.text.strip()
        if lastBuildDate is not None and lastBuildDate.text
        else None
    )

    items = []

    for item in channel.findall("item"):
        item_data = {}

        for tag in item_tags:
            element = item.find(tag)
            item_data[tag] = (
                element.text.strip()
                if element is not None and element.text
                else None
            )

        items.append(item_data)

    return {
        "LastBuildDate": last_build,
        "ItemCount": len(items),
        "Items": items,
    }


def getStatus(description: str) -> str | None:
    match = re.search(r"<b>Status:\s*(.*?)</b>", description or "", re.DOTALL)
    return match.group(1).strip() if match else None


def getAffectedComponents(description: str | None) -> List[str]:
    if not description:
        return []
    matches = re.findall(r"<li>([^<]+?)\s*\([^)]*\)</li>", description)
    return [m.strip() for m in matches if m.strip()]


def GUIDHash(logs: Dict) -> Dict[str, Any]:
    hashed_logs = {
        "LastBuildDate": logs["LastBuildDate"],
        "ItemCount": len(logs["Items"]),
        "Items": {},
    }
    for item in logs["Items"]:
        description = item.get("description")
        hashed_logs["Items"][item["guid"]] = {
            "Title": item["title"],
            "PubDate": item["pubDate"],
            "Status": getStatus(description),
            "Components": getAffectedComponents(description),
        }
    return hashed_logs


def compareState(
    old_state: Dict[str, Any] | None,
    new_state: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:

    changes = {
        "new": [],
        "updated": [],
        "resolved": [],
    }

    if old_state is None:
        for guid, data in new_state["Items"].items():
            changes["new"].append({"guid": guid, **data})
        return changes

    old_items = old_state.get("Items", {})
    new_items = new_state.get("Items", {})

    for guid, new_data in new_items.items():
        if guid not in old_items:
            changes["new"].append({"guid": guid, **new_data})
            continue

        old_status = old_items[guid].get("Status")
        new_status = new_data.get("Status")
        if old_status == new_status:
            continue

        payload = {
            "guid": guid,
            "Title": new_data.get("Title"),
            "OldStatus": old_status,
            "NewStatus": new_status,
            "PubDate": new_data.get("PubDate"),
            **new_data,
        }

        if new_status == "Resolved":
            changes["resolved"].append(payload)
        else:
            changes["updated"].append(payload)

    return changes
