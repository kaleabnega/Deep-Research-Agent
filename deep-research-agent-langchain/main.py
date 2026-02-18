#!/usr/bin/env python3

import argparse
import json
from app.agents.research_agent import DeepResearchAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deep research agent (LangChain)")
    parser.add_argument("question", help="Research question")
    parser.add_argument("--file", action="append", default=[], help="Path to a local file to ingest")
    parser.add_argument("--constraints", default="", help="JSON string of evidence constraints")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    constraints = None
    if args.constraints:
        try:
            constraints = json.loads(args.constraints)
        except json.JSONDecodeError:
            raise SystemExit("Invalid JSON in --constraints")
    agent = DeepResearchAgent()
    report = agent.run(question=args.question, file_paths=args.file, constraints=constraints)
    print(report)


if __name__ == "__main__":
    main()
