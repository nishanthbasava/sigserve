"""Golden test: the real sampler must approximately recover planted signatures.

Requires R + bayesNMF, so it runs inside the worker image:

    docker compose run --rm --no-deps -v ./tests:/app/tests worker \
        sh -c 'pip install -q ".[dev]" && pytest -m golden'
"""

import math

import pytest

from sigserve.sampler import run_bayesnmf

pytestmark = pytest.mark.golden

N_TYPES = 20
N_SAMPLES = 8
RANK = 2


def _true_signatures() -> list[list[float]]:
    # Two well-separated signatures: each concentrates 90% of its mass on a
    # disjoint half of the mutation types.
    signatures = []
    for i in range(N_TYPES):
        in_first_half = i < N_TYPES // 2
        a = 0.09 if in_first_half else 0.01
        b = 0.01 if in_first_half else 0.09
        signatures.append([a, b])
    return signatures


def _true_exposures() -> list[list[float]]:
    # Samples sweep from signature-A-dominant to signature-B-dominant, with
    # high totals so the signal dominates rounding noise.
    total = 2000.0
    exposures: list[list[float]] = [[], []]
    for j in range(N_SAMPLES):
        weight = j / (N_SAMPLES - 1)
        exposures[0].append(total * (1 - weight))
        exposures[1].append(total * weight)
    return exposures


def _matrix() -> list[list[int]]:
    signatures = _true_signatures()
    exposures = _true_exposures()
    return [
        [
            round(sum(signatures[i][k] * exposures[k][j] for k in range(RANK)))
            for j in range(N_SAMPLES)
        ]
        for i in range(N_TYPES)
    ]


def _cosine(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v, strict=True))
    return dot / math.sqrt(sum(a * a for a in u) * sum(b * b for b in v))


def test_recovers_planted_signatures() -> None:
    result = run_bayesnmf(_matrix(), {"rank": RANK, "max_iters": 1000})

    # Guard against a false pass on the stub engine outside the worker image.
    assert result.diagnostics["engine"] == "bayesNMF"

    estimated_columns = [
        [result.signatures[i][k] for i in range(N_TYPES)] for k in range(RANK)
    ]
    for true_column in zip(*_true_signatures(), strict=True):
        best = max(_cosine(list(true_column), est) for est in estimated_columns)
        assert best > 0.9, f"planted signature not recovered (best cosine {best:.3f})"
