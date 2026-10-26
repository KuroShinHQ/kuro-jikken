"""Tests for data/manifest.json: the only datasets an engine may read."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
REQUIRED = {"id", "title", "path", "in_repo", "licence", "domain", "used_by", "not_for"}


def test_ids_unique_and_required_fields_present():
    ids = [row["id"] for row in MANIFEST["datasets"]]
    assert len(ids) == len(set(ids))
    for row in MANIFEST["datasets"]:
        assert REQUIRED <= set(row), row["id"]
        assert row["not_for"], row["id"]


def test_licences_are_known():
    allowed = set(MANIFEST["allowed_licences"])
    for row in MANIFEST["datasets"]:
        assert row["licence"] in allowed, row["id"]


def test_repo_files_exist_with_recorded_hash():
    for row in MANIFEST["datasets"]:
        if not row["in_repo"] or not row["path"]:
            continue
        path = ROOT / row["path"]
        assert path.is_file(), row["id"]
        assert path.stat().st_size == row["bytes"], row["id"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == row["sha256"], row["id"]


def test_external_files_match_when_present():
    for row in MANIFEST["datasets"]:
        if row["in_repo"] or not row["path"] or not pathlib.Path(row["path"]).is_file():
            continue
        assert pathlib.Path(row["path"]).stat().st_size == row["bytes"], row["id"]
