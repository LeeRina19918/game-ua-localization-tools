#!/usr/bin/env python3
"""Pack translated TSV values into a binary common texts file."""
from __future__ import annotations

import argparse
import csv
import os
import re
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, List, Tuple

PLACEHOLDER_PATTERN = re.compile(r"%(?:%|[sdifux])")


@dataclass
class Entry:
    key: str
    value: str
    key_bytes: bytes


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

            entries.append(Entry(key=key, value=value, key_bytes=key_bytes))

        trailing = handle.read(1)
        if trailing:
            raise ValueError("Trailing bytes detected after parsing all entries")

    return version, entries


def read_tsv(path: Path) -> Tuple[int, Dict[str, Tuple[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if header is None:
            raise ValueError("TSV is empty")
        if len(header) < 4:
            raise ValueError("TSV header must have 4 columns")
        if header[:4] != ["id", "flags", "source", "translation"]:
            raise ValueError("TSV header must be: id\tflags\tsource\ttranslation")

        tsv_rows = 0
        mapping: Dict[str, Tuple[str, str]] = {}
        for row in reader:
            tsv_rows += 1
            if len(row) < 4:
                raise ValueError(
                    f"TSV row {tsv_rows + 1} has {len(row)} columns (expected 4)"
                )
            key = row[0]
            source = row[2]
            translation = row[3]
            mapping[key] = (source, translation)

    return tsv_rows, mapping


def placeholder_counts(text: str) -> Counter[str]:
    return Counter(PLACEHOLDER_PATTERN.findall(text))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply translations from TSV to binary common texts file."
    )
    parser.add_argument("--input", required=True, help="Path to original binary file")
    parser.add_argument("--tsv", required=True, help="Path to translated TSV file")
    parser.add_argument("--output", required=True, help="Path to output binary file")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow empty translations to overwrite original values",
    )
    parser.add_argument(
        "--strict-placeholders",
        action="store_true",
        help="Validate placeholders and newline counts before replacing",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    tsv_path = Path(args.tsv)
    output_path = Path(args.output)

    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1
    if not tsv_path.is_file():
        print(f"TSV file not found: {tsv_path}", file=sys.stderr)
        return 1

    try:
        version, entries = parse_binary(input_path)
    except ValueError as exc:
        print(f"Error parsing binary: {exc}", file=sys.stderr)
        return 1

    try:
        tsv_rows, tsv_mapping = read_tsv(tsv_path)
    except ValueError as exc:
        print(f"Error reading TSV: {exc}", file=sys.stderr)
        return 1

    missing_keys_in_tsv = 0
    replaced_count = 0
    skipped_empty_count = 0
    placeholder_errors: List[str] = []

    new_values: List[str] = []

    for entry in entries:
        tsv_entry = tsv_mapping.get(entry.key)
        if tsv_entry is None:
            missing_keys_in_tsv += 1
            new_values.append(entry.value)
            continue

        source, translation = tsv_entry
        if translation == "":
            if args.allow_empty:
                new_values.append("")
                replaced_count += 1
            else:
                new_values.append(entry.value)
                skipped_empty_count += 1
            continue

        if args.strict_placeholders:
            source_placeholders = placeholder_counts(source)
            translation_placeholders = placeholder_counts(translation)
            if source_placeholders != translation_placeholders:
                placeholder_errors.append(entry.key)
            if source.count("\n") != translation.count("\n"):
                placeholder_errors.append(entry.key)

        new_values.append(translation)
        replaced_count += 1

    if args.strict_placeholders and placeholder_errors:
        unique_keys = sorted(set(placeholder_errors))
        print("Placeholder or newline mismatch for keys:")
        for key in unique_keys:
            print(f"- {key}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", delete=False, dir=tmp_dir, prefix=output_path.name + ".tmp."
        ) as handle:
            tmp_name = handle.name
            handle.write(struct.pack("<II", version, len(entries)))
            for entry, value in zip(entries, new_values):
                value_bytes = value.encode("utf-16le")
                handle.write(struct.pack("<H", len(entry.key_bytes)))
                handle.write(entry.key_bytes)
                handle.write(struct.pack("<H", len(value_bytes) // 2))
                handle.write(value_bytes)
        os.replace(tmp_name, output_path)
    except OSError as exc:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
        print(f"Failed to write output binary: {exc}", file=sys.stderr)
        return 1

    print(f"entries_total: {len(entries)}")
    print(f"tsv_rows: {tsv_rows}")
    print(f"replaced_count: {replaced_count}")
    print(f"skipped_empty_count: {skipped_empty_count}")
    print(f"missing_keys_in_tsv_count: {missing_keys_in_tsv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
