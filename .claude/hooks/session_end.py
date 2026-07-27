from __future__ import annotations
import json
from guard_write import STATE, event

def main():
    STATE.mkdir(parents=True, exist_ok=True); (STATE / "interruption.json").write_text(json.dumps(event(), sort_keys=True) + "\n", encoding="utf-8")
if __name__ == "__main__": main()
