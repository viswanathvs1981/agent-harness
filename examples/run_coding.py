"""Run a goal through the generic harness (no API key required)."""

from pathlib import Path

from agent_harness import Harness
from agent_harness.llm import HeuristicLLM


def main() -> None:
    root = Path.cwd()
    h = Harness(project_root=root, llm=HeuristicLLM())
    try:
        result = h.run("implement a function to reverse a string", graph="coding")
        print(result.status, result.state.route)
        print(result.output)
        print("evals", result.eval_scores)
        print("promoted", result.promoted_skills)
    finally:
        h.close()


if __name__ == "__main__":
    main()
