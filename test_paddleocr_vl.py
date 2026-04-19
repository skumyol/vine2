#!/usr/bin/env python3
"""Test script for PaddleOCR-VL approach.

Usage:
    export PADDLEOCR_API_URL="https://your-paddleocr-endpoint.com"
    export PADDLEOCR_ACCESS_TOKEN="your-token"  # optional
    python test_paddleocr_vl.py path/to/wine_label.jpg
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.app.services.ocr_paddleocr_vl import (
    extract_ocr_text_paddleocr_vl,
    compare_ocr_approaches,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_paddleocr_vl.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print(f"\n🔍 Testing PaddleOCR-VL on: {image_path}")
    print("=" * 60)

    # Quick test
    text, snippets = extract_ocr_text_paddleocr_vl(image_path)

    if not text:
        print("❌ No text extracted")
        if snippets:
            print(f"Errors: {snippets}")
        sys.exit(1)

    print(f"\n✅ Extracted {len(text)} characters")
    print(f"✅ {len(snippets)} document chunks")

    print("\n--- EXTRACTED TEXT (first 800 chars) ---")
    print(text[:800])
    if len(text) > 800:
        print(f"\n... ({len(text) - 800} more characters)")

    # Compare with local OCR
    print("\n" + "=" * 60)
    print("📊 COMPARING WITH LOCAL OCR")
    print("=" * 60)

    comparison = compare_ocr_approaches(image_path)

    print(f"\nLocal OCR (Tesseract/EasyOCR):")
    print(f"  Length: {comparison['local']['length']} chars")
    print(f"  Snippets: {comparison['local']['snippets_count']}")

    print(f"\nPaddleOCR-VL (Cloud VLM):")
    print(f"  Length: {comparison['paddleocr_vl']['length']} chars")
    print(f"  Snippets: {comparison['paddleocr_vl']['snippets_count']}")

    # Save full comparison to file
    output_path = Path(image_path).with_suffix(".ocr_comparison.json")
    with open(output_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\n💾 Full comparison saved to: {output_path}")


if __name__ == "__main__":
    main()
