"""
Dore OS v2.0 — FFmpeg Audio Pipeline
Audio normalization, format conversion, waveform generation, stem splitting.
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, List


class FFmpegPipeline:
    """Audio processing pipeline using FFmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")

    # ─── Info ───────────────────────────────────────────────
    def probe(self, input_path: Path) -> Dict:
        """Get detailed audio metadata via ffprobe."""
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(input_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr}
        return json.loads(result.stdout)

    def get_duration(self, input_path: Path) -> float:
        """Get audio duration in seconds."""
        info = self.probe(input_path)
        try:
            return float(info.get("format", {}).get("duration", 0))
        except (ValueError, TypeError):
            return 0.0

    def get_loudness(self, input_path: Path) -> float:
        """Measure integrated loudness (LUFS) via loudnorm filter."""
        cmd = [
            self.ffmpeg, "-i", str(input_path), "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # loudnorm prints JSON to stderr
        for line in result.stderr.split("\n"):
            if "input_i" in line:
                try:
                    data = json.loads(line)
                    return float(data.get("input_i", 0))
                except json.JSONDecodeError:
                    pass
        return 0.0

    # ─── Normalization ──────────────────────────────────────
    def normalize(self, input_path: Path, output_path: Path,
                  target_lufs: float = -16.0, target_tp: float = -1.5) -> Dict:
        """Normalize audio to target LUFS level."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg, "-y", "-i", str(input_path),
            "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:linear=true:print_format=json",
            "-ar", "44100", "-ac", "2",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "input": str(input_path),
            "output": str(output_path),
            "target_lufs": target_lufs,
            "stderr": result.stderr[-500:] if result.stderr else "",
        }

    # ─── Format Conversion ──────────────────────────────────
    def convert(self, input_path: Path, output_path: Path,
                format_type: str = "mp3", bitrate: str = "320k") -> Dict:
        """Convert audio between formats."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        format_settings = {
            "mp3": ["-codec:a", "libmp3lame", "-b:a", bitrate],
            "flac": ["-codec:a", "flac", "-compression_level", "8"],
            "wav": ["-codec:a", "pcm_s16le"],
            "m4a": ["-codec:a", "aac", "-b:a", bitrate],
            "ogg": ["-codec:a", "libvorbis", "-b:a", bitrate],
        }

        settings = format_settings.get(format_type, format_settings["mp3"])
        cmd = [self.ffmpeg, "-y", "-i", str(input_path)] + settings + [str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "format": format_type,
            "output": str(output_path),
            "error": result.stderr[-300:] if result.returncode != 0 else "",
        }

    # ─── Master Prep ────────────────────────────────────────
    def master_prep(self, input_path: Path, output_dir: Path, release_slug: str) -> Dict:
        """Prepare all distribution formats from master WAV.

        Creates:
            {release_slug}_master.wav    (44.1kHz 16-bit)
            {release_slug}_master.flac   (lossless)
            {release_slug}_320.mp3       (320kbps MP3)
            {release_slug}_stream.mp3    (128kbps MP3 for preview)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}

        # Normalized master WAV
        master = output_dir / f"{release_slug}_master.wav"
        results["master_wav"] = self.normalize(input_path, master)

        # FLAC
        flac = output_dir / f"{release_slug}_master.flac"
        results["flac"] = self.convert(master, flac, "flac")

        # 320kbps MP3
        mp3_320 = output_dir / f"{release_slug}_320.mp3"
        results["mp3_320"] = self.convert(master, mp3_320, "mp3", "320k")

        # 128kbps MP3 (streaming preview)
        mp3_stream = output_dir / f"{release_slug}_stream.mp3"
        results["mp3_stream"] = self.convert(master, mp3_stream, "mp3", "128k")

        return {"release_slug": release_slug, "outputs": results}

    # ─── Waveform ───────────────────────────────────────────
    def generate_waveform(self, input_path: Path, output_path: Path,
                          width: int = 1200, height: int = 200,
                          color: str = "#7c3aed") -> Dict:
        """Generate waveform PNG from audio."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg, "-y", "-i", str(input_path),
            "-filter_complex",
            f"showwavespic=s={width}x{height}:colors={color}:split_channels=0",
            "-frames:v", "1", str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "output": str(output_path),
        }

    # ─── Stem Split (via demucs) ────────────────────────────
    def split_stems(self, input_path: Path, output_dir: Path,
                    model: str = "htdemucs") -> Dict:
        """Split audio into stems using demucs (if installed)."""
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "python3", "-m", "demucs", "--two-stems", "vocals",
                "-n", model, "-o", str(output_dir), str(input_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"status": "ok" if result.returncode == 0 else "error",
                    "output": str(output_dir), "model": model}
        except FileNotFoundError:
            return {
                "status": "skipped",
                "message": "demucs not installed. Install: pip install demucs"
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Stem splitting timed out (>5 min)"}
