"""Interface to the bayesNMF sampler.

`run_bayesnmf` is the single seam between SigServe and R: the worker calls it,
tests mock it, and the rpy2 bridge will replace its internals. The stub below
returns a deterministic fake factorization with the correct shapes.
"""

from dataclasses import dataclass
from typing import Any


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
