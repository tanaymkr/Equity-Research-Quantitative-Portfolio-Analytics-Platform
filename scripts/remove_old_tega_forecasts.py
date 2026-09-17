"""Remove the listed superseded forecasts from this repository checkout."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPORT_FILES = (
    "model.json",
    "forecast.md",
    "historical_checks.json",
    "historical_statements.html",
    "historical_statements.md",
    "reported_statements_used.json",
)
OLD_OUTPUT_FOLDERS = (
    "outputs/tega_fy2025",
    "outputs/tega_fy2026",
    "outputs/tega_model",
    "outputs/tega_downside",
    "outputs/tega_upside",
    "outputs/tega_scenarios",
)


def local_path(root: Path, relative: str) -> Path:
    path = root / relative
    if path == root or not path.resolve().is_relative_to(root):
        raise ValueError(f"Path is outside this checkout: {relative}")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"Symbolic link requires manual review: {relative}")
    return path


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def generated_reports(root: Path) -> set[Path]:
    targets = set()
    for name in OLD_OUTPUT_FOLDERS:
        directory = local_path(root, name)
        if not directory.exists():
            continue
        candidates = [directory] + [
            directory / s for s in ("base", "downside", "upside")
        ]
        for folder in candidates:
            model = local_path(root, str((folder / "model.json").relative_to(root)))
            if not model.is_file():
                continue
            try:
                result = json.loads(model.read_text(encoding="utf-8-sig"))
                base_year = result.get("base_year", result["assumptions"]["base_year"])
                if result["company"] != "Tega Industries Limited" or base_year not in (
                    2025,
                    2026,
                ):
                    continue
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            for filename in REPORT_FILES:
                path = local_path(root, str((folder / filename).relative_to(root)))
                if path.is_file():
                    targets.add(path)
        summary = local_path(
            root, str((directory / "scenarios.json").relative_to(root))
        )
        if summary.is_file():
            try:
                result = json.loads(summary.read_text(encoding="utf-8-sig"))
                if result.get("label") == "Historical FY2025; illustrative scenarios":
                    targets.add(summary)
                    markdown = local_path(
                        root, str(summary.with_suffix(".md").relative_to(root))
                    )
                    if markdown.is_file():
                        targets.add(markdown)
            except (ValueError, AttributeError):
                pass
    return targets


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        for required in (
            "run_tega_model.py",
            "examples/tega_fy2026_reported_statements.json",
            "examples/tega_molycop_facts.json",
            "examples/tega_molycop_assumptions.json",
        ):
            if not local_path(root, required).is_file():
                raise ValueError("Copy the complete update into the repository first.")
        manifest = json.loads(
            (root / "docs/TEGA_FORECAST_CLEANUP_FILES.json").read_text(encoding="utf-8")
        )
        targets = set()
        for entry in manifest["remove_files"]:
            path = local_path(root, entry["path"])
            if not path.exists():
                continue
            data = path.read_bytes()
            hashes = {blob_sha(data), blob_sha(data.replace(b"\r\n", b"\n"))}
            if entry["git_blob_sha"] not in hashes:
                raise ValueError(
                    f"This old file has local edits: {entry['path']}. "
                    "Review it in GitHub Desktop and remove it manually if intended. "
                    "No files were deleted by this run."
                )
            targets.add(path)
        generated = generated_reports(root)
        tracked_count = len(targets)
        targets.update(generated)
        for path in sorted(targets):
            path.unlink()
            print(f"Removed: {path.relative_to(root)}")
        parents = {
            parent
            for path in targets
            for parent in path.parents
            if parent != root and parent.is_relative_to(root)
        }
        for parent in sorted(parents, key=lambda p: len(p.parts), reverse=True):
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        print(
            f"Cleanup complete: {tracked_count} obsolete project files and {len(generated)} generated reports removed."
        )
        print("FY26 actuals and the combined Tega-Molycop DCF are retained.")
        print("Run Run_Tega_Model.bat for the combined model.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Cleanup stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
