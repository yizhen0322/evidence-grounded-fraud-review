"""Validate the exact recorded dashboard artifact chain without starting a server."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.artifacts import load_snapshot
from app.backend.settings import DashboardSettings


def validate_dashboard(config_path: str | Path) -> dict[str, Any]:
    """Return a public validation summary for the configured immutable snapshot."""
    settings = DashboardSettings.load(config_path)
    snapshot = load_snapshot(settings)
    provenance = snapshot.public_provenance()
    return {
        "valid": True,
        "case_count": len(snapshot.cases),
        "scenario_count": len(snapshot.scenarios),
        "recorded_narrative_arm": settings.config.recorded_narrative_arm,
        "source_chain_verified": bool(provenance["source_chain_verified"]),
        "run_ids": {
            stage: provenance[stage]["run_id"]
            for stage in ("detector", "g4", "g5", "results")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    try:
        result = validate_dashboard(arguments.config)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
