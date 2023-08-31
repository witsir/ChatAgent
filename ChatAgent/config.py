import json
from pathlib import Path

from dotenv import dotenv_values


def _get_user_agent_ua_local() -> dict | None:
    p = Path(__file__).parent / "user_agent_ua.in"
    if not p.exists():
        p.touch()
        return None
    else:
        with open(p, 'r') as f:
            return {"version_main": int(f.readline().strip()),
                    "User-Agent": f.readline().strip(),
                    "Sec-Ch-Ua": f.readline().strip()}


path = Path(__file__).parent / ".env"
config = dotenv_values(path.absolute())
config["ACCOUNTS"] = json.loads(config["ACCOUNTS"])
config["COV"] = json.loads((config["COV"]))
config["DEBUG"] = json.loads(config["DEBUG"])
config.setdefault("USER_AGENT_UA", _get_user_agent_ua_local())
