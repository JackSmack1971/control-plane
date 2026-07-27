from __future__ import annotations
import json
from guard_write import STATE, event, write_paths

def main():
    paths = [path for path in write_paths(event()) if path]
    if paths:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / "mutations.jsonl").open("a", encoding="utf-8", newline="\n") as out:
            out.write(json.dumps({"paths": paths}, sort_keys=True) + "\n")
if __name__ == "__main__": main()
