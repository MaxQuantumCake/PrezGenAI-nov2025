#!/usr/bin/env python3
"""Clean extracted page-wise text and produce normalized `.clean.txt` files."""
import argparse
import re
from pathlib import Path

# --- Constantes de configuration ---
HEADER_FOOTER_PATTERNS = [
    r"POUR LA SCIENCE\s*.*\d{4}",
    r"©.*",
    r"En application de la loi.*",
    r"Tous droits réservés.*",
    r"^.{0,6}/\s*POUR LA SCIENCE.*$",  # lignes type pied de page
]
SIGNIFICANT_CHAR_REGEX = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]")
PAGE_MARKER_REGEX = re.compile(r"\n=== PAGE (\d+) ===\n")
MAX_HEADING_LENGTH = 120
MIN_SIGNIFICANT_TOKEN_COUNT = 3


def remove_headers_footers(text: str) -> str:
    """Strip known header and footer patterns from a page."""

    for pat in HEADER_FOOTER_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE | re.MULTILINE)
    return text


def fix_hyphenation(text: str) -> str:
    """Collapse hyphenated line breaks back into single words."""

    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"-\n", "", text)
    return text


def is_significant_line(line: str) -> bool:
    """Return ``True`` when the line contains any significant character."""

    return bool(SIGNIFICANT_CHAR_REGEX.search(line))


def reflow_paragraphs(text: str) -> tuple[str, int, int]:
    """Merge meaningful lines into paragraphs and report statistics."""

    lines = text.splitlines()
    total_lines = 0
    kept_lines = 0
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer:
            paragraphs.append(" ".join(buffer))
            buffer = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            flush_buffer()
            continue
        if stripped_line.startswith("=== PAGE"):
            # Séparateur de page: on le relaiera ailleurs.
            flush_buffer()
            continue
        total_lines += 1
        if not is_significant_line(stripped_line):
            flush_buffer()
            continue
        kept_lines += 1
        if (
            stripped_line.isupper()
            and len(stripped_line) <= MAX_HEADING_LENGTH
            and len(SIGNIFICANT_CHAR_REGEX.findall(stripped_line))
            >= MIN_SIGNIFICANT_TOKEN_COUNT
        ):
            flush_buffer()
            paragraphs.append(stripped_line)
            continue
        buffer.append(stripped_line)

    flush_buffer()
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    cleaned = "\n\n".join(paragraphs)
    return cleaned, total_lines, kept_lines


def clean_page_text(page_text: str) -> tuple[str, int, int]:
    """Clean an individual page and return normalized text plus statistics."""

    text_content = remove_headers_footers(page_text)
    text_content = fix_hyphenation(text_content)
    cleaned_text, total_lines, kept_lines = reflow_paragraphs(text_content)
    return cleaned_text, total_lines, kept_lines


def process_file(txt_file_path: Path, output_directory: Path) -> None:
    """Clean a raw extracted text file and emit the `.clean.txt` output."""

    raw = txt_file_path.read_text(encoding="utf-8", errors="ignore")
    # Split on the page markers inserted during extraction.
    parts = PAGE_MARKER_REGEX.split(raw)
    if len(parts) <= 1:
        # pas de marqueurs: on nettoie en bloc
        cleaned = clean_page_text(raw)
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = output_directory / f"{txt_file_path.stem}.clean.txt"
        output_path.write_text(cleaned, encoding="utf-8")
        print(
            f"[OK] {txt_file_path.name} -> (sans pages) {txt_file_path.stem}.clean.txt"
        )
        return

    cleaned_pages: list[str] = []
    total_lines = 0
    kept_lines = 0
    for page_index in range(1, len(parts), 2):
        page_num = int(parts[page_index])
        page_text = parts[page_index + 1]
        cleaned_page_text, lines_total, lines_kept = clean_page_text(page_text)
        total_lines += lines_total
        kept_lines += lines_kept
        if cleaned_page_text:
            page_block = [f"=== PAGE {page_num} ===", cleaned_page_text]
            cleaned_pages.append("\n".join(page_block).rstrip())

    output_directory.mkdir(parents=True, exist_ok=True)
    out_path = output_directory / (txt_file_path.stem + ".clean.txt")
    cleaned_output = "\n\n".join(cleaned_pages)
    out_path.write_text(cleaned_output, encoding="utf-8")

    status = "[OK]" if kept_lines > 0 else "[WARN]"
    if total_lines == 0:
        detail = "aucune ligne textuelle détectée"
    else:
        detail = f"lignes retenues: {kept_lines}/{total_lines}"
    print(f"{status} {txt_file_path.name} -> {out_path.name} ({detail})")

def process_folder(dir, out):
    txts = sorted(p for p in dir.iterdir() if p.suffix.lower() == ".txt")
    if not txts:
        print(f"[INFO] Aucun .txt dans {dir}")
        return
    for txt in txts:
        process_file(txt, out)

def main():
    """CLI entry point for cleaning extracted text files page by page."""

    description = "Nettoyage texte par page (reflow, hyphens, headers/footers)."
    ap = argparse.ArgumentParser(description=description)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", "-f", type=Path, help="Fichier .txt extrait")
    g.add_argument("--dir", "-d", type=Path, help="Dossier de .txt extraits")
    ap.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("cleaned_txt"),
        help="Dossier de sortie",
    )
    args = ap.parse_args()

    if args.file:
        process_file(args.file, args.out)
    else:
        process_folder(args.dir, args.out)


if __name__ == "__main__":
    main()
