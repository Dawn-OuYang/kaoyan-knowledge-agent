from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import KaoyanAgent, KnowledgeBase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Invoke the Kaoyan Knowledge Agent Skill locally.")
    parser.add_argument("question", nargs="?", help="User question.")
    parser.add_argument("--input-json", default="", help="Read UTF-8 JSON payload from a file.")
    parser.add_argument("--output-json", default="", help="Write UTF-8 JSON result to a file.")
    parser.add_argument("--mode", default="qa", choices=["qa", "exam", "school", "plan"], help="Skill mode.")
    parser.add_argument("--specialty", default="全部", help="Specialty filter, such as 计算机, 通信工程, 法学.")
    parser.add_argument("--target", default="", help="Target school for planning mode.")
    parser.add_argument("--days", default="", help="Remaining study days for planning mode.")
    parser.add_argument("--level", default="", help="Current learning level for planning mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    kb = KnowledgeBase(ROOT / "data" / "knowledge_base.json")
    agent = KaoyanAgent(kb)
    if args.input_json:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    else:
        if not args.question:
            raise SystemExit("question is required unless --input-json is provided")
        payload = {
            "question": args.question,
            "mode": args.mode,
            "specialty": args.specialty,
            "profile": {
                "target": args.target,
                "days": args.days,
                "level": args.level,
            },
        }
    result = agent.invoke_skill(payload)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
