from __future__ import annotations
import subprocess
from guard_write import ROOT, allowed, emit, protected

def main():
    changed = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    changed = [line[3:].replace("\\", "/") for line in changed if len(line) > 3]
    forbidden, generated, _ = protected()
    bad = [p for p in changed if any(p == x or p.startswith(x + "/") for x in forbidden | generated)]
    bad += [path for path in changed if path.startswith(".claude/") and not allowed(path)[0]]
    if bad: emit("Stop", "dirty control-plane paths: " + ", ".join(sorted(set(bad))), stop=True)
if __name__ == "__main__": main()
