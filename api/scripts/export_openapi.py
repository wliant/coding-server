#!/usr/bin/env python3
"""Export FastAPI OpenAPI spec to openapi.json at the repository root."""
import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root: python api/scripts/export_openapi.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app

parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI spec")
parser.add_argument(
    "--output",
    type=Path,
    default=Path(__file__).parent.parent.parent / "openapi.json",
    help="Path to write the OpenAPI spec JSON (default: openapi.json at repo root)",
)
args = parser.parse_args()

output_path: Path = args.output
output_path.parent.mkdir(parents=True, exist_ok=True)
spec = app.openapi()
output_path.write_text(json.dumps(spec, indent=2))
print(f"OpenAPI spec written to {output_path}")
