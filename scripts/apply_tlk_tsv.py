#!/usr/bin/env python3
import os
import sys
import xml.etree.ElementTree as ET


def unescape_tsv_field(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\\\", "\\")
    )


def parse_tsv(tsv_path: str):
    rows = []
    with open(tsv_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if line_number == 1:
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                raise ValueError(
                    f"Line {line_number}: expected 4 columns, found {len(parts)}"
                )
            entry_id, flags, source, translation = parts
            rows.append((entry_id, flags, source, translation))
    return rows


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: apply_tlk_tsv.py <input_xml> <input_tsv> <output_xml>", file=sys.stderr)
        return 1

    input_xml = sys.argv[1]
    input_tsv = sys.argv[2]
    output_xml = sys.argv[3]

    if not os.path.isfile(input_xml):
        print(f"Input XML not found: {input_xml}", file=sys.stderr)
        return 1
    if not os.path.isfile(input_tsv):
        print(f"Input TSV not found: {input_tsv}", file=sys.stderr)
        return 1

    try:
        with open(input_xml, "r", encoding="utf-8-sig") as handle:
            tree = ET.parse(handle)
    except ET.ParseError as exc:
        print(f"Failed to parse XML: {exc}", file=sys.stderr)
        return 1

    try:
        rows = parse_tsv(input_tsv)
    except ValueError as exc:
        print(f"Failed to parse TSV: {exc}", file=sys.stderr)
        return 1

    root = tree.getroot()
    strings_by_id = {}
    for string_elem in root.iter("string"):
        id_elem = string_elem.find("id")
        if id_elem is None or id_elem.text is None:
            continue
        entry_id = id_elem.text.strip()
        if entry_id:
            strings_by_id[entry_id] = string_elem

    total_rows = len(rows)
    non_empty_translations = 0
    updates_applied = 0
    missing_ids = []

    for entry_id, _flags, _source, translation in rows:
        if translation.strip() == "":
            continue
        non_empty_translations += 1
        string_elem = strings_by_id.get(entry_id)
        if string_elem is None:
            if len(missing_ids) < 20:
                missing_ids.append(entry_id)
            continue
        data_elem = string_elem.find("data")
        if data_elem is None:
            data_elem = ET.SubElement(string_elem, "data")
        data_elem.text = unescape_tsv_field(translation)
        updates_applied += 1

    os.makedirs(os.path.dirname(output_xml) or ".", exist_ok=True)
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)

    print(f"TSV rows read: {total_rows}")
    print(f"Translations provided: {non_empty_translations}")
    print(f"Entries updated: {updates_applied}")
    print(f"Missing ids in XML: {len(missing_ids)}")
    if missing_ids:
        print("Missing ids (up to 20): " + ", ".join(missing_ids))

    if updates_applied == 0 and non_empty_translations > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
