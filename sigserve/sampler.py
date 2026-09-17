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


def run_bayesnmf(matrix: list[list[int]], params: dict[str, Any]) -> SamplerResult:
    engine = get_settings().sampler_engine
    if engine == "auto":
        engine = "bayesnmf" if importlib.util.find_spec("rpy2") else "stub"

    if engine == "stub":
        return _run_stub(matrix, params)

    from sigserve.rpy2_bridge import run_sampler

    return run_sampler(matrix, params)


def _run_stub(matrix: list[list[int]], params: dict[str, Any]) -> SamplerResult:
    rank = params["rank"]
    n_types = len(matrix)
    n_samples = len(matrix[0]) if matrix else 0

    # Uniform signatures; exposures split each sample's total counts evenly
    # across factors, so column totals are conserved like a real factorization.
    signatures = [[1.0 / n_types] * rank for _ in range(n_types)]
    column_totals = [sum(row[j] for row in matrix) for j in range(n_samples)]
    exposures = [[total / rank for total in column_totals] for _ in range(rank)]

    return SamplerResult(
        signatures=signatures,
        exposures=exposures,
        diagnostics={"engine": "stub", "converged": True, "n_iterations": 0},
    )
