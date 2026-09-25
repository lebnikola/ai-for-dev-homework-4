from __future__ import annotations

import argparse
import sys

from agent import run_agent
from config import ConfigError
from respond import format_response


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-operator of the finance operations API")
    parser.add_argument(
        "query",
        help='natural language request, e.g. "запиши покупку продуктов на 5000"',
    )
    args = parser.parse_args()

    try:
        run_result = run_agent(args.query)
    except ConfigError as exc:
        print(format_response({"tool_log": [], "llm_error": str(exc)}))
        return 1

    output = format_response(run_result)
    print(output)
    return 0 if output.startswith("Status: success") else 1


if __name__ == "__main__":
    sys.exit(main())
