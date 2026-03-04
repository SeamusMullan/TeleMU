"""CLI entry-point for verifying .tmu file integrity.

Usage::

    telemu-verify session.tmu
    telemu-verify --repair session.tmu --output repaired.tmu
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from telemu.recording.tmu_format import repair_file, verify_file


def main(argv: list[str] | None = None) -> int:
    """Run the ``telemu-verify`` CLI."""
    parser = argparse.ArgumentParser(
        prog="telemu-verify",
        description="Verify or repair .tmu recording files",
    )
    parser.add_argument("file", type=Path, help="Path to the .tmu file")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Attempt to repair by copying valid frames to a new file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for repaired file (default: <file>.repaired.tmu)",
    )
    args = parser.parse_args(argv)

    tmu_path: Path = args.file
    if not tmu_path.exists():
        print(f"Error: file not found: {tmu_path}", file=sys.stderr)
        return 1

    result = verify_file(tmu_path)
    print(result.message)

    if result.ok:
        return 0

    if not args.repair:
        return 2

    # Repair mode
    out_path: Path = args.output or tmu_path.with_suffix(".repaired.tmu")
    recovered, skipped = repair_file(tmu_path, out_path)
    print(f"Repair complete: {recovered} frames recovered, {skipped} skipped → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
