#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="input/GlobalTlk_tlk.xml"
OUTPUT_FILE="locale/uk.csv"

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Не знайдено файл $INPUT_FILE. Завантажте його у папку input/" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

python scripts/extract_tlk_xml.py "$INPUT_FILE" "$OUTPUT_FILE"

echo "Готово! CSV збережено тут: $OUTPUT_FILE"
