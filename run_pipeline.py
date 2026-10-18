
"""
Runs the full pipeline: ingest -> load -> dbt build.
Stops at the first failure and logs output to logs/pipeline.log.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
LOG_FILE = PROJECT_DIR / "logs" / "pipeline.log"


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
    """Run one pipeline step and stop if it fails."""
    logging.info("Starting %s", name)

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        for line in result.stdout.splitlines():
            logging.info("  %s", line)

    if result.returncode != 0:
        if result.stderr:
            logging.error("%s", result.stderr.strip())
        if result.stdout:
            logging.error("%s", result.stdout.strip())
        raise SystemExit(result.returncode)

    if result.stderr:
        for line in result.stderr.splitlines():
            logging.info("  %s", line)

    logging.info("Finished %s", name)


def main() -> None:
    os.chdir(PROJECT_DIR)
    setup_logging()

    logging.info("===== Pipeline run started =====")

    dbt_executable = shutil.which("dbt")
    if not dbt_executable:
        logging.error(
            "dbt executable not found. Check that dbt is installed "
            "and available on your PATH."
        )
        raise SystemExit(1)

    run_step("ingest", [sys.executable, "ingest.py"])
    run_step("load", [sys.executable, "load.py"])
    run_step(
        "dbt build",
        [
            dbt_executable,
            "build",
            "--project-dir", str(PROJECT_DIR / "dbt"),
            "--profiles-dir", str(PROJECT_DIR / "dbt"),
        ]
    )
    run_step("export", [sys.executable, "export.py"])
    

    logging.info("===== Pipeline run finished successfully =====")


if __name__ == "__main__":
    main()
