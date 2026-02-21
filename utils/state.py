import json
from pathlib import Path
from typing import Any, Dict, Optional

STATE_FILE = Path("state.json")

def loadState() -> Optional[Dict[str, Any]]:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return None

def saveState(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))