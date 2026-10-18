"""
Runs the full pipeline: ingest -> load -> dbt build -> export -> forecast.
Stops at the first failure and logs output to logs/pipeline.log.

Usage:
    python run_pipeline.py
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
LOG_FILE = PROJECT_DIR / "logs" / "pipeline.log"

# Use the dbt installed next to this Python (inside .venv on the laptop,
# inside the runner's Python on GitHub Actions).
DBT = (shutil.which("dbt", path=str(Path(sys.executable).parent))
       or shutil.which("dbt")
       or "dbt")


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def run_step(name: str, command: list[str]) -> None:
    """Run one pipeline step as its own program and stop if it fails."""
    logging.info("Starting %s", name)
    result = subprocess.run(command, cwd=PROJECT_DIR, capture_output=True, text=True)

    for line in result.stdout.splitlines():
        logging.info("  %s", line)

    if result.returncode != 0:
        if result.stderr:
            logging.error("%s failed:\n%s", name, result.stderr.strip())
        raise SystemExit(result.returncode)

    logging.info("Finished %s", name)


def main() -> None:
    os.chdir(PROJECT_DIR)
    setup_logging()
    logging.info("===== Pipeline run started =====")

    run_step("dbt version check", [DBT, "--version"])
    run_step("ingest", [sys.executable, "ingest.py"])
    run_step("load", [sys.executable, "load.py"])
    run_step("dbt build", [DBT, "build",
                           "--project-dir", str(PROJECT_DIR / "dbt"),
                           "--profiles-dir", str(PROJECT_DIR / "dbt")])
    run_step("export", [sys.executable, "export.py"])

    if (PROJECT_DIR / "forecast" / "train.py").exists():
        run_step("forecast", [sys.executable, "forecast/train.py"])

    logging.info("===== Pipeline run finished successfully =====")


if __name__ == "__main__":
    main()