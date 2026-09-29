from __future__ import annotations
import argparse, json, tempfile
from pathlib import Path
from scenarios.run_scenarios import run_all, scenario_a, scenario_b, scenario_c, scenario_d


def main():
    p = argparse.ArgumentParser(description="Reliable AI Workflow Demo")
    p.add_argument("scenario", choices=["a", "b", "c", "d", "all"], nargs="?", default="all")
    args = p.parse_args()
    if args.scenario == "b": print(json.dumps(scenario_b(), indent=2)); return
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "demo.sqlite")
        value = scenario_a(db) if args.scenario == "a" else scenario_c(db) if args.scenario == "c" else scenario_d(db) if args.scenario == "d" else run_all()
    print(json.dumps(value, indent=2))


if __name__ == "__main__": main()
