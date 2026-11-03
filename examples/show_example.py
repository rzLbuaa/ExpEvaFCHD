import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Display authored synthetic examples; no model inference is performed.")
    parser.add_argument("--case", choices=("demonstration", "multifamily", "insufficient"), default="demonstration")
    parser.add_argument("--section", choices=("all", "input", "evidence", "output", "trace"), default="all")
    args = parser.parse_args()
    path = Path(__file__).resolve().parent / f"{args.case}.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    payload = bundle if args.section == "all" else {
        "example_kind": bundle["example_kind"],
        args.section: bundle[args.section],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
