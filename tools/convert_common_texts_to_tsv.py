#!/usr/bin/env python3
import csv
import struct
import string
from collections import OrderedDict
from pathlib import Path

ALLOWED = set(string.ascii_letters + string.digits + "_")

def is_key_bytes(b: bytes) -> bool:
    if not b:
        return False
    try:
        s = b.decode("ascii")
    except Exception:
        return False
    if "_" not in s:
        return False
    return all(ch in ALLOWED for ch in s)

def is_utf16_text(b: bytes) -> bool:
    if len(b) % 2 != 0:
        return False
    try:
        s = b.decode("utf-16le")
    except Exception:
        return False
    if not s:
        return False
    printable = sum(ch.isprintable() and ch not in "\x0b\x0c" for ch in s)
    return (printable / len(s)) >= 0.9

def scan_records(data: bytes):
    pos = 0
    n = len(data)
    out = []
    while pos + 4 < n:
        L = struct.unpack_from("<H", data, pos)[0]
        # ключі зазвичай короткі
        if 0 < L < 200 and pos + 2 + L + 2 <= n:
            keyb = data[pos + 2 : pos + 2 + L]
            if is_key_bytes(keyb):
                S = struct.unpack_from("<H", data, pos + 2 + L)[0]
                if 0 < S < 4000 and pos + 2 + L + 2 + S * 2 <= n:
                    valb = data[pos + 2 + L + 2 : pos + 2 + L + 2 + S * 2]
                    if is_utf16_text(valb):
                        key = keyb.decode("ascii")
                        val = valb.decode("utf-16le")
                        out.append((key, val))
                        pos = pos + 2 + L + 2 + S * 2
                        continue
        pos += 1
    return out

def main(inp: str, out_tsv: str):
    data = Path(inp).read_bytes()
    recs = scan_records(data)

    dedup = OrderedDict()
    for k, v in recs:
        if k not in dedup:
            dedup[k] = v

    out_path = Path(out_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "flags", "source", "translation"])
        for k in sorted(dedup.keys()):
            w.writerow([k, 1, dedup[k], ""])

    print(f"OK: {len(dedup)} rows -> {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python convert_common_texts_to_tsv.py <input_file> <output_tsv>")
    main(sys.argv[1], sys.argv[2])
