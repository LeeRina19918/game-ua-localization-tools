#!/usr/bin/env python3
import os
import sys
import xml.etree.ElementTree as ET


def escape_tsv(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: extract_tlk_xml.py <input_xml> <output_tsv>", file=sys.stderr)
        return 1

    input_xml = sys.argv[1]
    output_tsv = sys.argv[2]

    if not os.path.isfile(input_xml):
        print(f"Input file not found: {input_xml}", file=sys.stderr)
        return 1

    try:
        with open(input_xml, "r", encoding="utf-8-sig") as handle:
            tree = ET.parse(handle)
    except ET.ParseError as exc:
        print(f"Failed to parse XML: {exc}", file=sys.stderr)
        return 1

    root = tree.getroot()
    rows = []

    for string_elem in root.iter("string"):
        id_elem = string_elem.find("id")
        if id_elem is None or id_elem.text is None:
            continue
        entry_id = id_elem.text.strip()
        if not entry_id:
            continue

        flags_elem = string_elem.find("flags")
        flags = ""
        if flags_elem is not None and flags_elem.text is not None:
            flags = flags_elem.text.strip()

        data_elem = string_elem.find("data")
        source = ""
        if data_elem is not None and data_elem.text is not None:
            source = data_elem.text

        rows.append([
            escape_tsv(entry_id),
            escape_tsv(flags),
            escape_tsv(source),
            escape_tsv("")
        ])

    if not rows:
        print("No <string> entries with <id> found.", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(output_tsv) or ".", exist_ok=True)
    with open(output_tsv, "w", encoding="utf-8", newline="") as handle:
        handle.write("id\tflags\tsource\ttranslation\n")
        for row in rows:
            handle.write("\t".join(row) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
