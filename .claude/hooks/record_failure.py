from __future__ import annotations
import json
from guard_write import STATE, event

def main():
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "failures.jsonl").open("a", encoding="utf-8", newline="\n").write(json.dumps(event(), sort_keys=True) + "\n")
if __name__ == "__main__": main()
