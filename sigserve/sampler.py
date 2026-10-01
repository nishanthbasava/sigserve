"""Interface to the bayesNMF sampler.

`run_bayesnmf` is the single seam between SigServe and R: the worker calls it
and tests mock it. Engine selection is driven by the `sampler_engine` setting:
"auto" uses the real rpy2 bridge when rpy2 is installed (the worker image) and
falls back to a deterministic stub otherwise (dev machines, unit tests).
"""

import importlib.util
from dataclasses import dataclass
from typing import Any

from sigserve.config import get_settings
from sigserve.progress import update_progress


@dataclass
class SamplerResult:
    signatures: list[list[float]]  # n_mutation_types x rank
    exposures: list[list[float]]  # rank x n_samples
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "signatures": self.signatures,
            "exposures": self.exposures,
            "diagnostics": self.diagnostics,
        }


def resolve_rank_range(params: dict[str, Any]) -> tuple[int, int]:
    """Fixed `rank` wins; otherwise the [rank_min, rank_max] range.

    Tolerates params recorded before the range fields existed."""
    rank = params.get("rank")
    if rank is not None:
        return rank, rank
    return params.get("rank_min", 2), params.get("rank_max", 8)


def run_bayesnmf(
    matrix: list[list[int]], params: dict[str, Any], job_id: str | None = None
) -> SamplerResult:
    engine = get_settings().sampler_engine
    if engine == "auto":
        engine = "bayesnmf" if importlib.util.find_spec("rpy2") else "stub"

    if engine == "stub":
        return _run_stub(matrix, params, job_id)

    from sigserve.rpy2_bridge import run_sampler

    return run_sampler(matrix, params, job_id)


def _run_stub(
    matrix: list[list[int]], params: dict[str, Any], job_id: str | None = None
) -> SamplerResult:
    rank_min, rank_max = resolve_rank_range(params)
    rank = (rank_min + rank_max) // 2
    max_iters = params.get("max_iters", 2000)
    n_types = len(matrix)
    n_samples = len(matrix[0]) if matrix else 0

    update_progress(job_id, "sampling", log_tail=[f"stub sampler, rank {rank}"])

    # Uniform signatures; exposures split each sample's total counts evenly
    # across factors, so column totals are conserved like a real factorization.
    signatures = [[1.0 / n_types] * rank for _ in range(n_types)]
    column_totals = [sum(row[j] for row in matrix) for j in range(n_samples)]
    exposures = [[total / rank for total in column_totals] for _ in range(rank)]

    # A plausible-looking trace so result pages render identically in
    # stub-backed environments.
    points = 10
    iters = [max(1, max_iters * (i + 1) // points) for i in range(points)]
    trace = {
        "iter": iters,
        "rmse": [round(1.0 / (i + 1), 4) for i in range(points)],
        "loglikelihood": [round(-100.0 / (i + 1), 4) for i in range(points)],
        "logposterior": [round(-110.0 / (i + 1), 4) for i in range(points)],
        "bic": [round(200.0 / (i + 1), 4) for i in range(points)],
        "rank": [rank] * points,
    }

    return SamplerResult(
        signatures=signatures,
        exposures=exposures,
        diagnostics={
            "engine": "stub",
            "converged": True,
            "converged_at": iters[-1],
            "estimated_rank": rank,
            "rank_min": rank_min,
            "rank_max": rank_max,
            "seed": params.get("seed"),
            "max_iters": max_iters,
            "trace": trace,
        },
    )
