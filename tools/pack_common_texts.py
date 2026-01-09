#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import struct
import sys
from pathlib import Path

def load_translations(tsv_path: Path) -> dict[str, str]:
    """
    TSV columns expected: id, flags, source, translation
    We only use: id, translation
    """
    translations: dict[str, str] = {}
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or "id" not in reader.fieldnames or "translation" not in reader.fieldnames:
            raise ValueError("TSV must have columns: id, flags, source, translation")

        for row in reader:
            key = (row.get("id") or "").strip()
            tr = row.get("translation") or ""
            if not key or not tr:
                continue

            # If your workflow stores newlines as literal "\n" in TSV — convert to real newline.
            tr = tr.replace("\\n", "\n")
            translations[key] = tr

    return translations

def is_ascii_printable(b: bytes) -> bool:
    return all(32 <= c <= 126 for c in b)

def pack_file(orig_path: Path, tsv_path: Path, out_path: Path) -> None:
    data = orig_path.read_bytes()
    if len(data) < 8:
        raise ValueError("Input file too small")

    ver = struct.unpack_from("<I", data, 0)[0]
    count = struct.unpack_from("<I", data, 4)[0]

    translations = load_translations(tsv_path)

    buf = bytearray()
    buf += struct.pack("<II", ver, count)

    off = 8
    n = len(data)

    for i in range(count):
        if off + 4 > n:
            raise ValueError(f"Unexpected EOF while reading record {i}")

        (len_id,) = struct.unpack_from("<H", data, off)
        off += 2

        id_bytes = data[off:off + len_id]
        off += len_id

        if len(id_bytes) != len_id or not is_ascii_printable(id_bytes):
            raise ValueError(f"Bad id bytes at record {i}")

        id_str = id_bytes.decode("ascii", errors="strict")

        (len_text,) = struct.unpack_from("<H", data, off)
        off += 2

        text_bytes = data[off:off + 2 * len_text]
        off += 2 * len_text

        try:
            orig_text = text_bytes.decode("utf-16le")
        except UnicodeDecodeError as e:
            raise ValueError(f"Bad utf-16le text at record {i} (id={id_str})") from e

        new_text = translations.get(id_str, "")
        if not new_text:
            new_text = orig_text

        new_text_bytes = new_text.encode("utf-16le")
        # len_text is stored as number of UTF-16 code units == Python len() for normal BMP text.
        # Works fine for Ukrainian and most cases.
        buf += struct.pack("<H", len_id)
        buf += id_bytes
        buf += struct.pack("<H", len(new_text))
        buf += new_text_bytes

    if off != n:
        # If this triggers, your file may contain extra tail data after the last record.
        # In that case: append the remaining bytes unchanged.
        buf += data[off:]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf)

def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: pack_common_texts.py <input_original_file> <input_translated_tsv> <output_file>", file=sys.stderr)
        return 2

    orig_path = Path(sys.argv[1])
    tsv_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    pack_file(orig_path, tsv_path, out_path)
    print(f"OK: wrote {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
