import time
from typing import Any


def run_job(matrix: list[list[int]], params: dict[str, Any]) -> dict[str, Any]:
    """Placeholder task; replaced by the bayesNMF sampler in a later phase."""
    time.sleep(0.5)
    return {
        "note": "dummy result",
        "n_mutation_types": len(matrix),
        "n_samples": len(matrix[0]) if matrix else 0,
        "rank": params["rank"],
    }
