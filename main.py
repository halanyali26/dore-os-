#!/usr/bin/env python3
"""
Dore OS v2.0 — AI Music Label Operating System
Main entry point and CLI.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.core import PipelineRunner, ReleaseState
from pipeline.vault_manager import VaultManager
from pipeline.state_machine import StateMachine, State
from pipeline.isrc import ISRCGenerator, UPCGenerator
from pipeline.linter import GuardianLinter
from pipeline.ffmpeg_pipeline import FFmpegPipeline
from pipeline.observability import get_observability


BASE_PATH = Path(os.getenv("DORE_OS_HOME", Path(__file__).parent))


def cmd_bootstrap(args):
    """Initialize Dore OS for a new artist or release."""
    vm = VaultManager(BASE_PATH)

    if args.artist and args.release:
        state = vm.bootstrap_release(args.artist, args.release,
                                     args.title or args.release,
                                     args.genre or "electronic")
        print(f"✅ Release bootstrapped: {args.artist}/{args.release}")
        print(f"   State: {state['state']}")
        print(f"   Vault: vault/sources/{args.artist}-{args.release}.md")
    elif args.artist:
        # Create artist folder with template
        artist_path = BASE_PATH / "artists" / args.artist
        artist_path.mkdir(parents=True, exist_ok=True)
        (artist_path / "releases").mkdir(exist_ok=True)

        # Copy template
        template = BASE_PATH / "artists" / "_template" / "state.json"
        if template.exists():
            import shutil
            shutil.copy(template, artist_path / "info.json")

        vm.write_wiki_page("entities", args.artist,
                          f"# {args.artist}\n\nAI Music Artist\nStatus: ACTIVE\n",
                          {"title": args.artist, "tags": ["artist", "ai-music"]})
        vm.update_index("entities", args.artist, f"Artist: {args.artist}")
        vm.append_log("bootstrap", f"New artist: {args.artist}")
        print(f"✅ Artist created: {args.artist}")
    else:
        print("Usage: dore-os bootstrap --artist <name> [--release <slug>] [--title <title>] [--genre <genre>]")


def cmd_state(args):
    """Show or transition release state."""
    sm = StateMachine()

    if args.transition:
        from_state = State(args.from_state.upper())
        to_state = State(args.to.upper())
        result = sm.transition(from_state, to_state,
                              {"artist": args.artist, "release": args.release})

        if result["success"]:
            vm = VaultManager(BASE_PATH)
            vm.set_state(args.artist, args.release, to_state.value, "CLI")
            print(f"✅ {from_state.value} → {to_state.value}")
            print(f"   {result['description']}")
            if result.get("required_files"):
                print(f"   Required: {', '.join(result['required_files'])}")
            if result.get("auto_actions"):
                print(f"   Auto: {', '.join(result['auto_actions'])}")
        else:
            print(f"❌ {result['error']}")
            if result.get("valid_next"):
                print(f"   Valid next states: {', '.join(result['valid_next'])}")
    else:
        # Show current state and valid transitions
        vm = VaultManager(BASE_PATH)
        state_data = vm.get_state(args.artist, args.release)
        current = State(state_data["state"])
        valid = sm.get_valid_next_states(current)

        print(f"📊 {args.artist}/{args.release}")
        print(f"   State: {current.value}")
        print(f"   History: {len(state_data.get('history', []))} transitions")
        print(f"   Valid next: {', '.join(s.value for s in valid)}")


def cmd_ingest(args):
    """Run LLM-Wiki ingest pattern on raw files."""
    obs = get_observability()
    trace = obs.trace("ingest", {"path": args.path}) if obs.enabled else None
    trace_id = trace.id if trace else None

    runner = PipelineRunner(BASE_PATH)
    task = {"agent": "curator", "action": "generate_idea",
            "artist_id": args.artist or "default",
            "genre": args.genre or "electronic",
            "mood": args.mood or "dark"}
    result = runner.execute(task)
    print(f"✅ Ingest complete: {result}")


def cmd_query(args):
    """Query the wiki and optionally file back the answer."""
    vm = VaultManager(BASE_PATH)

    results = vm.search_wiki(args.question)
    print(f"🔍 Wiki search: \"{args.question}\"\n")
    if not results:
        print("   No results found.")
        return

    for r in results[:10]:
        print(f"   {r['path']} ({r['size']} chars)")

    if args.file_back and results:
        answer = f"Query results for: {args.question}\n\nRelevant pages:\n"
        for r in results[:5]:
            answer += f"- {r['path']}\n"
        path = vm.file_back_query(args.question, answer,
                                  [r['path'] for r in results[:5]])
        print(f"\n✅ Filed back to: {path}")


def cmd_lint(args):
    """Run Guardian health checks."""
    linter = GuardianLinter(BASE_PATH / "vault")
    report = linter.full_check()

    print(f"🔍 Dore OS Guardian Report — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"   Issues: {report['total_issues']}")
    for sev, count in report['by_severity'].items():
        if count:
            print(f"   {sev}: {count}")
    print(f"   Full report: vault/alerts/ALERTS.md")


def cmd_isrc(args):
    """Generate ISRC and UPC codes."""
    isrc_gen = ISRCGenerator()
    isrc = isrc_gen.generate(args.artist, args.release)
    print(f"ISRC: {isrc}")
    print(f"Valid: {'✅' if ISRCGenerator.validate(isrc) else '❌'}")

    upc_gen = UPCGenerator()
    upc = upc_gen.generate(args.release)
    print(f"UPC:  {upc}")


def cmd_audio(args):
    """Process audio: normalize, convert, master prep."""
    ffmpeg = FFmpegPipeline()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"❌ File not found: {args.input}")
        return

    output_dir = Path(args.output) if args.output else input_path.parent

    if args.action == "info":
        info = ffmpeg.probe(input_path)
        fmt = info.get("format", {})
        print(f"Duration: {fmt.get('duration', '?')}s")
        print(f"Format: {fmt.get('format_name', '?')}")
        print(f"Size: {int(fmt.get('size', 0)) / 1024 / 1024:.1f}MB")

    elif args.action == "normalize":
        output = output_dir / f"{input_path.stem}_norm.wav"
        result = ffmpeg.normalize(input_path, output)
        print(f"✅ Normalized: {result['output']}" if result["status"] == "ok" else f"❌ {result['stderr']}")

    elif args.action == "master":
        result = ffmpeg.master_prep(input_path, output_dir, input_path.stem)
        print(f"✅ Master prepared: {output_dir}")
        for fmt_name, r in result["outputs"].items():
            status = "✅" if r.get("status") == "ok" else "❌"
            print(f"   {status} {fmt_name}")

    elif args.action == "waveform":
        output = output_dir / f"{input_path.stem}_waveform.png"
        result = ffmpeg.generate_waveform(input_path, output)
        print(f"✅ Waveform: {output}" if result["status"] == "ok" else "❌")


def cmd_musicbrainz(args):
    """Look up artist/recording on MusicBrainz."""
    from pipeline.musicbrainz import MusicBrainzClient
    mb = MusicBrainzClient()

    if args.action == "artist":
        results = mb.search_artist(args.query)
        for a in results:
            print(f"  {a['mbid']} — {a['name']} ({a['type']}, {a['country']})")
    elif args.action == "recording":
        results = mb.search_recording(args.query)
        for r in results:
            isrcs = ", ".join(r.get("isrcs", [])) or "none"
            print(f"  {r['mbid']} — {r['title']} [{r['artist']}] ISRC: {isrcs}")


def cmd_ddex(args):
    """Generate DDEX ERN XML for a release."""
    from pipeline.ddex import DDEXGenerator
    gen = DDEXGenerator()

    data = {
        "release_reference": f"DORE-{args.artist}-{args.release}-{datetime.now():%Y%m%d}",
        "title": args.title or args.release,
        "artist_name": args.artist,
        "label_name": "Dore Studio",
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "tracks": [{"title": args.release, "isrc": args.isrc or "", "duration_iso": "PT3M30S"}],
    }
    xml = gen.generate_release(data)
    output = BASE_PATH / "vault" / "analytics" / f"{args.release}_ddex.xml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(xml)
    print(f"✅ DDEX XML written: {output}")


def cmd_run(args):
    """Run a full pipeline task."""
    runner = PipelineRunner(BASE_PATH)

    task = {
        "agent": args.agent,
        "action": args.action,
        "artist_id": args.artist,
        "release_slug": args.release,
        "genre": args.genre,
    }
    result = runner.execute(task)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Dore OS v2.0 — AI Music Label Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # bootstrap
    p = subparsers.add_parser("bootstrap", help="Create artist or release")
    p.add_argument("--artist", required=True)
    p.add_argument("--release")
    p.add_argument("--title")
    p.add_argument("--genre")
    p.set_defaults(func=cmd_bootstrap)

    # state
    p = subparsers.add_parser("state", help="View or transition release state")
    p.add_argument("--artist", required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--transition", action="store_true")
    p.add_argument("--from-state", dest="from_state")
    p.add_argument("--to", dest="to")
    p.set_defaults(func=cmd_state)

    # ingest
    p = subparsers.add_parser("ingest", help="Run LLM-Wiki ingest")
    p.add_argument("--path", default=".")
    p.add_argument("--artist")
    p.add_argument("--genre")
    p.add_argument("--mood")
    p.set_defaults(func=cmd_ingest)

    # query
    p = subparsers.add_parser("query", help="Search wiki and optionally file back")
    p.add_argument("question", help="The question to search for")
    p.add_argument("--file-back", action="store_true", help="Save answer to syntheses/")
    p.set_defaults(func=cmd_query)

    # lint
    p = subparsers.add_parser("lint", help="Run Guardian health check")
    p.set_defaults(func=cmd_lint)

    # isrc
    p = subparsers.add_parser("isrc", help="Generate ISRC/UPC codes")
    p.add_argument("--artist", required=True)
    p.add_argument("--release", required=True)
    p.set_defaults(func=cmd_isrc)

    # audio
    p = subparsers.add_parser("audio", help="Process audio with FFmpeg")
    p.add_argument("action", choices=["info", "normalize", "master", "waveform"])
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o")
    p.set_defaults(func=cmd_audio)

    # musicbrainz
    p = subparsers.add_parser("musicbrainz", help="MusicBrainz lookup")
    p.add_argument("action", choices=["artist", "recording"])
    p.add_argument("query")
    p.set_defaults(func=cmd_musicbrainz)

    # ddex
    p = subparsers.add_parser("ddex", help="Generate DDEX XML")
    p.add_argument("--artist", required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--title")
    p.add_argument("--isrc")
    p.set_defaults(func=cmd_ddex)

    # run
    p = subparsers.add_parser("run", help="Execute pipeline task")
    p.add_argument("--agent", required=True, choices=["curator", "packager", "distributor", "guardian"])
    p.add_argument("--action", default="run")
    p.add_argument("--artist", required=True)
    p.add_argument("--release")
    p.add_argument("--genre")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
