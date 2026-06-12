from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from backend.app.db.migrate_legacy import FullMigrationReport, MigrationReport, migrate_all


def _format_step(name: str, report: MigrationReport) -> str:
    lines = [
        f"[{name}] inserted={report.inserted} updated={report.updated} skipped={report.skipped} conflicts={report.conflicts}",
    ]
    lines.extend(f"  - {detail}" for detail in report.details)
    return "\n".join(lines)


def format_report(report: FullMigrationReport) -> str:
    sections = [
        f"MallSenseAI legacy migration report (dry_run={report.dry_run})",
        _format_step("cameras", report.cameras),
        _format_step("scenes", report.scenes),
        _format_step("rois", report.rois),
        _format_step("rules", report.rules),
        "JSON:",
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
    ]
    return "\n\n".join(sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MallSenseAI legacy data migration.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview planned changes without writing to the database or assets.")
    mode.add_argument("--real-run", action="store_true", help="Apply migration changes. Idempotent and non-destructive to legacy files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.real_run
    if args.dry_run:
        dry_run = True
    print(format_report(migrate_all(dry_run=dry_run)))


if __name__ == "__main__":
    main()
