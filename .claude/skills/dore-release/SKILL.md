---
name: dore-release-pipeline
description: "Dore OS release pipeline workflow: from IDEA to MONETIZED. Use when creating new releases, transitioning states, or debugging pipeline issues."
version: 1.0
---

# Dore OS Release Pipeline

## State Machine
```
IDEA → PRODUCTION → MASTERED → PACKAGED → DISTRIBUTED → LIVE → MONETIZED → ARCHIVED
```

## Workflow
1. **IDEA**: Generate concept, lyrics, genre via Curator agent
2. **PRODUCTION**: Create audio stems, rough mix
3. **MASTERED**: FFmpeg normalize, convert to FLAC/MP3
4. **PACKAGED**: Assign ISRC/UPC, generate DDEX XML, prepare metadata
5. **DISTRIBUTED**: Upload to YouTube (Composio), DistroKid (Playwright)
6. **LIVE**: Confirmed on streaming platforms
7. **MONETIZED**: First royalty received

## Key Commands
```bash
python3 main.py bootstrap --artist X --release Y --title "Z" --genre "G"
python3 main.py state --artist X --release Y
python3 main.py isrc --artist X --release Y
python3 main.py lint
python3 main.py query "search term" --file-back
```

## Files
- `artists/{artist}/releases/{release}/state.json` — state + history
- `vault/sources/{artist}-{release}.md` — wiki page
- `pipeline/core.py` — agent implementations
