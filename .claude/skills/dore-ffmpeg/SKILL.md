---
name: dore-ffmpeg
description: "FFmpeg audio pipeline for Dore OS: normalize, convert, master prep, waveform generation. Use when processing audio files for releases."
version: 1.0
---

# Dore OS FFmpeg Audio Pipeline

## Commands
```bash
# Info
python3 main.py audio info -i track.wav

# Normalize to -16 LUFS
python3 main.py audio normalize -i track.wav -o output/

# Full master prep (WAV + FLAC + MP3 320 + MP3 128)
python3 main.py audio master -i track.wav -o output/

# Waveform PNG
python3 main.py audio waveform -i track.wav -o output/
```

## Target Specs
- Sample rate: 44100 Hz
- Channels: 2 (stereo)
- LUFS: -16.0 (streaming standard)
- True peak: -1.5 dB
- Formats: WAV 16-bit, FLAC, MP3 320kbps, MP3 128kbps

## Module
`pipeline/ffmpeg_pipeline.py` — FFmpegPipeline class
