"""Local playtime reported by Subnautica's standard-profile save slots."""
import json
import math
import re

def subnautica_slots(library):
    saves = library / "steamapps/common/Subnautica/SNAppData/SavedGames"
    slots = []
    for file in sorted(saves.glob("slot*/gameinfo.json")):
        slot = file.parent.name
        if not re.fullmatch(r"slot[0-9]{4}", slot):
            continue
        try:
            if file.stat().st_size > 65536:
                continue
            data = json.loads(file.read_text(encoding="utf-8-sig"))
            seconds = data.get("gameTime")
            if data.get("corrupted") or type(seconds) not in (float, int) or not math.isfinite(seconds) or seconds < 0:
                continue
            slots.append(dict(slot=slot, seconds=int(seconds)))
        except (OSError, ValueError, AttributeError, OverflowError):
            continue
    return slots
