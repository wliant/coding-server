#!/usr/bin/env python3
"""Export FastAPI OpenAPI spec to openapi.json at the repository root."""
import json
import sys
from pathlib import Path

# Allow running from repo root: python api/scripts/export_openapi.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app

output_path = Path(__file__).parent.parent.parent / "openapi.json"
spec = app.openapi()
output_path.write_text(json.dumps(spec, indent=2))
print(f"OpenAPI spec written to {output_path}")
