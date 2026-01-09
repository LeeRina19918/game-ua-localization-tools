#!/usr/bin/env python3
"""Extract localization entries from binary common texts file into TSV."""
from __future__ import annotations

import argparse
import csv
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, List


@dataclass
class Entry:
    key: str
    value: str


def read_exact(handle: BinaryIO, size: int) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise ValueError("Unexpected end of file while reading binary data")
    return data


def parse_binary(path: Path) -> tuple[int, List[Entry]]:
    with path.open("rb") as handle:
        header = read_exact(handle, 8)
        version, count = struct.unpack("<II", header)
        entries: List[Entry] = []

        for _ in range(count):
            key_len_bytes = struct.unpack("<H", read_exact(handle, 2))[0]
            key_bytes = read_exact(handle, key_len_bytes)
            try:
                key = key_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Failed to decode key as UTF-8: {exc}") from exc

            value_len_units = struct.unpack("<H", read_exact(handle, 2))[0]
            value_bytes = read_exact(handle, value_len_units * 2)
            try:
                value = value_bytes.decode("utf-16le")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Failed to decode value as UTF-16LE: {exc}") from exc

            entries.append(Entry(key=key, value=value))

        trailing = handle.read(1)
        if trailing:
            raise ValueError("Trailing bytes detected after parsing all entries")

    return version, entries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract common texts binary into TSV."
    )
    parser.add_argument("--input", required=True, help="Path to input binary file")
    parser.add_argument("--output", required=True, help="Path to output TSV file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        _version, entries = parse_binary(input_path)
    except ValueError as exc:
        print(f"Error parsing binary: {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["id", "flags", "source", "translation"])
            for entry in entries:
                writer.writerow([entry.key, "1", entry.value, ""])
    except OSError as exc:
        print(f"Failed to write TSV: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
