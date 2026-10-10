"""Generate web/public/sample-dataset.csv (samples x 96 contexts).

Three planted signatures with distinct substitution-class profiles and
smoothly varying exposures across 30 samples, Poisson noise on the
expected counts. Also writes the planted signature profiles to
web/public/sample-signatures.json so the landing page can show the
dataset's ground truth as example output. Deterministic:
python scripts/make_sample_dataset.py rewrites the same files
byte-for-byte.
"""

import csv
import json
import math
import random
from pathlib import Path

SUBSTITUTIONS = ["C>A", "C>G", "C>T", "T>A", "T>C", "T>G"]
BASES = ["A", "C", "G", "T"]
CONTEXTS = [f"{f}[{s}]{t}" for s in SUBSTITUTIONS for f in BASES for t in BASES]

N_SAMPLES = 30
RNG = random.Random(7)


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    # Knuth; fine for the small per-cell rates used here.
    threshold = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def normalized(weights: dict[str, float]) -> list[float]:
    """Expand per-class weights into a 96-length distribution with
    deterministic per-context jitter."""
    raw = []
    for i, context in enumerate(CONTEXTS):
        substitution = context[2:5]
        base = weights.get(substitution, 0.02)
        jitter = 0.4 + 1.2 * ((math.sin(i * 12.9898) * 43758.5453) % 1.0)
        raw.append(base * jitter)
    total = sum(raw)
    return [value / total for value in raw]


SIGNATURE_NAMES = [
    "SBS1-like (C>T dominant)",
    "SBS4-like (C>A dominant)",
    "SBS5-like (flat, T>C leaning)",
]

SIGNATURES = [
    # SBS1-like: C>T dominant
    normalized({"C>T": 1.0, "C>A": 0.05, "C>G": 0.05}),
    # SBS4-like: C>A dominant
    normalized({"C>A": 1.0, "C>G": 0.15, "T>A": 0.1}),
    # SBS5-like: T>C leaning, flatter
    normalized({"T>C": 0.8, "T>G": 0.25, "C>T": 0.2, "T>A": 0.15}),
]


def main() -> None:
    out_path = Path(__file__).resolve().parent.parent / "web" / "public" / "sample-dataset.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for j in range(N_SAMPLES):
        # Exposure mix sweeps across the cohort so each signature
        # dominates somewhere; totals vary between ~800 and ~2600.
        sweep = j / (N_SAMPLES - 1)
        mix = [
            max(0.05, 1.2 * (1 - sweep)),
            max(0.05, 1.2 * sweep),
            0.5 + 0.4 * math.sin(math.pi * sweep),
        ]
        total = 800 + int(1800 * ((j * 37) % N_SAMPLES) / N_SAMPLES)
        scale = total / sum(mix)
        exposures = [m * scale for m in mix]
        counts = [
            poisson(RNG, sum(SIGNATURES[k][i] * exposures[k] for k in range(3)))
            for i in range(96)
        ]
        rows.append([f"sample_{j + 1:02d}", *counts])

    with out_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", *CONTEXTS])
        writer.writerows(rows)
    print(f"wrote {out_path} ({N_SAMPLES} samples x 96 contexts)")

    signatures_path = out_path.parent / "sample-signatures.json"
    signatures_path.write_text(
        json.dumps(
            {
                "contexts": CONTEXTS,
                "signatures": [
                    {"name": name, "profile": [round(v, 6) for v in profile]}
                    for name, profile in zip(SIGNATURE_NAMES, SIGNATURES, strict=True)
                ],
            },
            separators=(",", ":"),
        )
        + "\n"
    )
    print(f"wrote {signatures_path} ({len(SIGNATURES)} planted signatures)")


if __name__ == "__main__":
    main()
