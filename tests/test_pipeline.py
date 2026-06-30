"""
Dore OS v2.0 — Test Suite
=========================
"""

import json
import tempfile
from pathlib import Path

from pipeline.isrc import ISRCGenerator, UPCGenerator
from pipeline.state_machine import StateMachine, State
from pipeline.vault_manager import VaultManager
from pipeline.linter import GuardianLinter
from pipeline.ddex import DDEXGenerator


def test_isrc_generation():
    gen = ISRCGenerator()
    isrc = gen.generate("volt", "static-pulse")
    assert ISRCGenerator.validate(isrc), f"Invalid ISRC: {isrc}"
    assert isrc.startswith("TR-DRS-"), f"Wrong prefix: {isrc}"
    parts = isrc.split("-")
    assert len(parts) == 4, f"Wrong format: {isrc}"


def test_upc_generation():
    gen = UPCGenerator()
    upc = gen.generate("test-album")
    assert len(upc) == 12, f"UPC must be 12 digits: {upc}"
    assert upc.isdigit(), f"UPC not digits: {upc}"


def test_state_machine_valid_transitions():
    sm = StateMachine()
    assert sm.can_transition(State.IDEA, State.PRODUCTION)
    assert sm.can_transition(State.PRODUCTION, State.MASTERED)
    assert sm.can_transition(State.MASTERED, State.PACKAGED)
    assert sm.can_transition(State.PACKAGED, State.DISTRIBUTED)
    assert sm.can_transition(State.DISTRIBUTED, State.LIVE)
    assert sm.can_transition(State.LIVE, State.MONETIZED)


def test_state_machine_invalid_transition():
    sm = StateMachine()
    assert not sm.can_transition(State.IDEA, State.LIVE)
    result = sm.transition(State.IDEA, State.LIVE)
    assert not result["success"]
    assert "Invalid transition" in result["error"]


def test_state_machine_rollback():
    sm = StateMachine()
    assert sm.can_transition(State.PRODUCTION, State.IDEA)
    assert sm.can_transition(State.MASTERED, State.PRODUCTION)


def test_ddex_generation():
    gen = DDEXGenerator()
    data = {
        "release_reference": "TEST-001",
        "title": "Test Track",
        "artist_name": "Test Artist",
        "label_name": "Dore Studio",
        "release_date": "2026-06-30",
        "tracks": [{"title": "Test Track", "isrc": "TR-DRS-26-00001", "duration_iso": "PT3M30S"}],
    }
    xml = gen.generate_release(data)
    assert "NewReleaseMessage" in xml
    assert "TEST-001" in xml
    assert "Test Track" in xml
    assert "TR-DRS-26-00001" in xml


def test_vault_manager_bootstrap():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        vm = VaultManager(base)
        state = vm.bootstrap_release("test-artist", "test-release", "Test Release", "electronic")
        assert state["state"] == "IDEA"
        assert state["title"] == "Test Release"

        # Check state file
        sf = base / "artists" / "test-artist" / "releases" / "test-release" / "state.json"
        assert sf.exists()

        # Check wiki source
        ws = base / "vault" / "sources" / "test-artist-test-release.md"
        assert ws.exists()


def test_linter_missing_isrc():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        vm = VaultManager(base)
        vm.bootstrap_release("art", "rel", "Test", "electronic")

        # Set state to PACKAGED but no ISRC
        vm.set_state("art", "rel", "PACKAGED", "test")

        linter = GuardianLinter(base / "vault")
        issues = linter.check_missing_isrc()
        assert len(issues) >= 1
        assert issues[0]["type"] == "missing_isrc"


def test_linter_cross_references():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        vault = base / "vault"
        vault.mkdir(parents=True)

        # Create a page with dead link
        (vault / "sources").mkdir()
        (vault / "sources" / "test.md").write_text("See [[nonexistent]] page.\nAlso [[sources/test]] is fine.\n")

        linter = GuardianLinter(vault)
        issues = linter.check_cross_references()
        dead_links = [i for i in issues if i["type"] == "dead_link"]
        assert len(dead_links) >= 1
        assert "nonexistent" in dead_links[0]["message"]
