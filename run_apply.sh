#!/usr/bin/env bash
set -euo pipefail

INPUT_XML="${1:-input/GlobalTlk_tlk.xml}"
INPUT_TSV="${2:-locale/uk.tsv}"
OUTPUT_XML="${3:-output/GlobalTlk_tlk.uk.xml}"

if [[ ! -f "$INPUT_XML" ]]; then
  echo "Не знайдено файл $INPUT_XML. Завантажте його у папку input/" >&2
  exit 1
fi

if [[ ! -f "$INPUT_TSV" ]]; then
  echo "Не знайдено файл $INPUT_TSV. Запустіть спочатку run_extract.sh" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_XML")"

python scripts/apply_tlk_tsv.py "$INPUT_XML" "$INPUT_TSV" "$OUTPUT_XML"

echo "Готово! Оновлений XML збережено тут: $OUTPUT_XML"
