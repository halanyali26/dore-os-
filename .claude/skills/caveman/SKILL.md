---
name: caveman
description: "Strip narration and fluff from LLM responses. Reduce output tokens 65-75%. Use when pipeline agents produce verbose output that needs compression."
version: 1.0
---

# Caveman Mode — Token Compression

## Levels
1. **Light**: Remove pleasantries, keep structure
2. **Medium**: Strip intro/outro, keep only facts
3. **Heavy**: Raw data only, no prose

## Trigger
Add to any prompt: "Respond in caveman mode: no narration, no pleasantries, only the data."

## Pipeline Usage
```python
# In agent prompts
prompt = f"{base_prompt}\nRespond concisely. No narration."
```
