# Official Documentation Pack

## Purpose

Generated first-party Claude Code and Model Context Protocol documentation. This pack is reference input, not project configuration.

## Entry Points

- `README.md` — pack scope, source policy, and usage sequence.
- `AGENT_INDEX.md` — human-readable navigation map.
- `index/chunks.jsonl` — searchable chunks for topic discovery.
- `docs/` — full captured pages.
- `manifest.json` and `sources.csv` — generation metadata and provenance.

## Contracts & Invariants

- Search `index/chunks.jsonl`, then read the matching full page under `docs/`.
- Base claims on each page's `source_url` provenance rather than memory.
- Keep the pack limited to first-party or otherwise approved official documentation sources.
- Treat the snapshot date in `README.md` and `manifest.json` as a freshness boundary.
- Regenerate pack artifacts together; do not hand-edit a captured page without updating its index and metadata.

## Anti-patterns

- Do not cite `AGENT_INDEX.md` as the substantive source when a full page exists.
- Do not assume this snapshot is current for version-sensitive behavior.
