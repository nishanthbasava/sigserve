"""Generate web/public/cosmic-sbs.json from the COSMIC SBS catalog.

Downloads the COSMIC v3.4 SBS GRCh37 reference catalog (or reads a local
copy passed as argv[1]) and writes it as compact JSON: contexts in the
canonical 96 order, one 96-vector per signature, values rounded to five
decimals. The web results page computes cosine similarity against this
file client-side; the API never sees it.
"""

import csv
import json
import sys
import urllib.request
from pathlib import Path

CATALOG_URL = (
    "https://cog.sanger.ac.uk/cosmic-signatures-production/documents/COSMIC_v3.4_SBS_GRCh37.txt"
)
CATALOG_VERSION = "COSMIC v3.4 SBS GRCh37"

SUBSTITUTIONS = ["C>A", "C>G", "C>T", "T>A", "T>C", "T>G"]
BASES = ["A", "C", "G", "T"]
CONTEXTS = [f"{f}[{s}]{t}" for s in SUBSTITUTIONS for f in BASES for t in BASES]


def main() -> None:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text()
    else:
        with urllib.request.urlopen(CATALOG_URL) as response:
            text = response.read().decode()

    rows = list(csv.reader(text.strip().splitlines(), delimiter="\t"))
    header, body = rows[0], rows[1:]
    names = header[1:]
    by_context = {row[0]: [float(value) for value in row[1:]] for row in body}

    missing = [context for context in CONTEXTS if context not in by_context]
    if missing:
        raise SystemExit(f"catalog is missing {len(missing)} contexts, e.g. {missing[0]}")

    signatures = {
        name: [round(by_context[context][k], 5) for context in CONTEXTS]
        for k, name in enumerate(names)
    }

    out_path = Path(__file__).resolve().parent.parent / "web" / "public" / "cosmic-sbs.json"
    out_path.write_text(
        json.dumps(
            {"version": CATALOG_VERSION, "contexts": CONTEXTS, "signatures": signatures},
            separators=(",", ":"),
        )
        + "\n"
    )
    print(f"wrote {out_path} ({len(signatures)} signatures)")


if __name__ == "__main__":
    main()
