from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from engine import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Tong hop hanh kiem / ren luyen chay local")
parser.add_argument("--source", default=str(ROOT))
parser.add_argument("--output", default=str(ROOT / "outputs"))
args = parser.parse_args()
result = run_pipeline(args.source, args.output)
print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
