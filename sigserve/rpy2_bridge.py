"""rpy2 bridge to the bayesNMF R package.

Only imported when rpy2 is installed (the worker image); the import of rpy2
itself is deferred into `run_sampler` so the RQ work-horse fork, not the
long-lived worker parent, initializes embedded R.
"""

import tempfile
import time
from typing import Any

import numpy as np

from sigserve.sampler import SamplerResult

_FIT_FUNCTION = """
function(data, rank, likelihood, prior, miniters, maxiters, map_over, map_every, output_dir) {
    ctrl <- bayesNMF::new_convergence_control(
        miniters = miniters, maxiters = maxiters,
        MAP_over = map_over, MAP_every = map_every
    )
    res <- bayesNMF::bayesNMF(
        data = data, rank = rank,
        likelihood = likelihood, prior = prior,
        convergence_control = ctrl,
        output_dir = output_dir, overwrite = TRUE
    )
    converged <- res$converged_at
    list(
        P = res$MAP$P,
        E = res$MAP$E,
        converged_at = if (is.null(converged) || length(converged) == 0) -1 else converged
    )
}
"""


def run_sampler(matrix: list[list[int]], params: dict[str, Any]) -> SamplerResult:
    import rpy2.robjects as ro
    from rpy2.robjects import default_converter, numpy2ri

    rank = params["rank"]
    max_iters = params.get("max_iters", 2000)
    likelihood = params.get("likelihood", "poisson")
    prior = params.get("prior", "truncnormal")

    # Package defaults assume >=1000 iterations; scale the convergence
    # windows down so small max_iters values remain valid.
    miniters = min(1000, max_iters)
    map_over = min(1000, max(50, max_iters // 4))
    map_every = min(100, max(10, max_iters // 20))

    data = np.asarray(matrix, dtype=float)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="bayesnmf-") as output_dir:
        with (default_converter + numpy2ri.converter).context():
            fit = ro.r(_FIT_FUNCTION)(
                data,
                rank,
                likelihood,
                prior,
                miniters,
                max_iters,
                map_over,
                map_every,
                output_dir,
            )
            signatures = np.asarray(fit.getbyname("P"))
            exposures = np.asarray(fit.getbyname("E"))
            converged_at = int(np.asarray(fit.getbyname("converged_at"))[0])
    elapsed = time.monotonic() - started

    return SamplerResult(
        signatures=signatures.tolist(),
        exposures=exposures.tolist(),
        diagnostics={
            "engine": "bayesNMF",
            "likelihood": likelihood,
            "prior": prior,
            "converged": converged_at > 0,
            "converged_at": converged_at if converged_at > 0 else None,
            "max_iters": max_iters,
            "elapsed_seconds": round(elapsed, 2),
        },
    )
