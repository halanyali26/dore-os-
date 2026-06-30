---
name: dore-vault-wiki
description: "Dore OS Obsidian vault LLM-Wiki pattern: INGEST, QUERY, LINT. Use when managing the knowledge base, adding sources, or querying the wiki."
version: 1.0
---

# Dore OS Vault — LLM-Wiki Pattern

Based on Karpathy's LLM Wiki + knowledge-pipeline (selmakcby).

## Operations
- **INGEST**: New source → read → summarize → write wiki page → update index → update cross-refs → log
- **QUERY**: Read index → find relevant pages → synthesize answer → optionally file back to syntheses/
- **LINT**: Check contradictions, stale claims, orphans, missing ISRC, corrupt audio

## Commands
```bash
python3 main.py ingest --artist X --genre G
python3 main.py query "question" --file-back
python3 main.py lint
```

## Vault Structure
```
vault/
├── CLAUDE.md     # Schema/rules
├── index.md      # Content catalog
├── log.md        # Chronological log
├── raw/          # Immutable sources
├── sources/      # Source summaries
├── entities/     # Artists, platforms
├── concepts/     # Abstract ideas
├── decisions/    # Architecture decisions
├── syntheses/    # Filed-back queries
├── analytics/    # JSON data
├── alerts/       # Guardian reports
└── archive/      # Old pages (never deleted)
```

## Hard Rules
1. `raw/` immutable — only user writes
2. Every claim sourced
3. Contradictions flagged, not deleted
4. Bidirectional links
5. Every operation logged
6. Pages archived, never deleted
