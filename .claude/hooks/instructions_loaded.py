from __future__ import annotations
import json
from guard_write import STATE, event

def main():
    data = event(); STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "instructions.jsonl").open("a", encoding="utf-8", newline="\n").write(json.dumps({"path": data.get("file_path"), "reason": data.get("load_reason")}, sort_keys=True) + "\n")
if __name__ == "__main__": main()
