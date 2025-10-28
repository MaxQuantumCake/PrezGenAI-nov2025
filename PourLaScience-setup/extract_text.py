#!/usr/bin/env python3
"""Extract plain text from PDFs and insert page markers."""
import argparse
from pathlib import Path

import fitz  # PyMuPDF


def extract_pdf_to_txt(pdf_path: Path, out_dir: Path) -> None:
    """Extract raw text from a PDF and persist it with page markers."""

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[ERROR] Ouverture échouée: {pdf_path} -> {e}")
        return

    all_text = []
    for i, page in enumerate(doc):
        text = page.get_text("text")  # extraction brute
        all_text.append(f"\n=== PAGE {i+1} ===\n{text}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (pdf_path.stem + ".txt")
    out_path.write_text("\n".join(all_text), encoding="utf-8")
    print(f"[OK] {pdf_path.name} -> {out_path.name} (pages: {len(doc)})")

def extract_text_from_folder(dir, out):
    pdfs = sorted(p for p in dir.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"[INFO] Aucun PDF trouvé dans {dir}")
        return
    for pdf in pdfs:
        extract_pdf_to_txt(pdf, out)

def main() -> None:
    """CLI entry point for extracting text from PDFs into `.txt` files."""

    description = "Extraction brute texte depuis PDFs (PyMuPDF)."
    parser = argparse.ArgumentParser(description=description)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", "-f", type=Path, help="Un PDF à traiter")
    g.add_argument("--dir", "-d", type=Path, help="Dossier contenant des PDFs")
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("extracted_txt"),
        help="Dossier de sortie .txt",
    )
    args = parser.parse_args()

    if args.file:
        extract_pdf_to_txt(args.file, args.out)
    else:
        if not args.dir.exists():
            print(f"[ERROR] Dossier introuvable: {args.dir}")
            return
        extract_text_from_folder(args.dir, args.out)


if __name__ == "__main__":
    main()
