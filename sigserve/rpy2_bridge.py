"""rpy2 bridge to the bayesNMF R package.

Only imported when rpy2 is installed (the worker image); the import of rpy2
itself is deferred into `run_sampler` so the RQ work-horse fork, not the
long-lived worker parent, initializes embedded R.

Progress: embedded R holds the GIL for the whole fit, so no Python thread in
this process can run while R samples. A small forked helper process tails the
sampler's log.txt into the job row instead; it is killed when the fit returns.
"""

import glob
import multiprocessing
import os
import tempfile
import time
from typing import Any

import numpy as np

from sigserve.sampler import SamplerResult, resolve_rank_range

LOG_TAIL_LINES = 15
LOG_POLL_SECONDS = 3.0

_FIT_FUNCTION = """
function(data, rank_min, rank_max, likelihood, prior,
         miniters, maxiters, map_over, map_every, seed, output_dir) {
    if (seed >= 0) set.seed(seed)
    ctrl <- bayesNMF::new_convergence_control(
        miniters = miniters, maxiters = maxiters,
        MAP_over = map_over, MAP_every = map_every
    )
    rank <- if (rank_min == rank_max) rank_min else rank_min:rank_max
    res <- bayesNMF::bayesNMF(
        data = data, rank = rank,
        likelihood = likelihood, prior = prior,
        convergence_control = ctrl,
        output_dir = output_dir, overwrite = TRUE,
        periodic_save = FALSE
    )
    # run_gibbs_sampler ends with get_MAP(final = TRUE), so MAP$P / MAP$E
    # are already subset to the learned rank.
    converged <- res$state$converged_iter
    metrics <- res$state$MAP_metrics
    list(
        P = res$MAP$P,
        E = res$MAP$E,
        converged_at = if (is.null(converged) || length(converged) == 0) -1 else converged,
        trace_iter = metrics$iter,
        trace_rmse = metrics$RMSE,
        trace_loglik = metrics$loglikelihood,
        trace_logpost = metrics$logposterior,
        trace_bic = metrics$BIC,
        trace_rank = metrics$rank
    )
}
"""


def run_sampler(
    matrix: list[list[int]], params: dict[str, Any], job_id: str | None = None
) -> SamplerResult:
    import rpy2.robjects as ro
    from rpy2.robjects import default_converter, numpy2ri

    rank_min, rank_max = resolve_rank_range(params)
    max_iters = params.get("max_iters", 2000)
    seed = params.get("seed")
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
        tailer = _spawn_log_tailer(output_dir, job_id)
        try:
            with (default_converter + numpy2ri.converter).context():
                fit = ro.r(_FIT_FUNCTION)(
                    data,
                    rank_min,
                    rank_max,
                    likelihood,
                    prior,
                    miniters,
                    max_iters,
                    map_over,
                    map_every,
                    -1 if seed is None else int(seed),
                    output_dir,
                )
                signatures = np.asarray(fit.getbyname("P"))
                exposures = np.asarray(fit.getbyname("E"))
                converged_at = int(np.asarray(fit.getbyname("converged_at"))[0])
                trace = {
                    "iter": _int_list(fit.getbyname("trace_iter")),
                    "rmse": _float_list(fit.getbyname("trace_rmse")),
                    "loglikelihood": _float_list(fit.getbyname("trace_loglik")),
                    "logposterior": _float_list(fit.getbyname("trace_logpost")),
                    "bic": _float_list(fit.getbyname("trace_bic")),
                    "rank": _int_list(fit.getbyname("trace_rank")),
                }
        finally:
            if tailer is not None:
                tailer.terminate()
                tailer.join(timeout=5)
    elapsed = time.monotonic() - started

    return SamplerResult(
        signatures=signatures.tolist(),
        exposures=exposures.tolist(),
        diagnostics={
            "engine": "bayesNMF",
            "bayesnmf_ref": os.environ.get("BAYESNMF_REF"),
            "likelihood": likelihood,
            "prior": prior,
            "converged": converged_at > 0,
            "converged_at": converged_at if converged_at > 0 else None,
            "estimated_rank": int(signatures.shape[1]),
            "rank_min": rank_min,
            "rank_max": rank_max,
            "seed": seed,
            "max_iters": max_iters,
            "elapsed_seconds": round(elapsed, 2),
            "trace": trace,
        },
    )


def _float_list(vector: Any) -> list[float | None]:
    # R NA becomes NaN, which is not valid JSON; map non-finite to None.
    values = np.asarray(vector, dtype=float).ravel()
    return [round(float(v), 6) if np.isfinite(v) else None for v in values]


def _int_list(vector: Any) -> list[int | None]:
    values = np.asarray(vector, dtype=float).ravel()
    return [int(v) if np.isfinite(v) else None for v in values]


def _spawn_log_tailer(output_dir: str, job_id: str | None) -> Any:
    if job_id is None:
        return None
    process = multiprocessing.Process(
        target=_tail_log_loop, args=(output_dir, job_id), daemon=True
    )
    process.start()
    return process


def _tail_log_loop(output_dir: str, job_id: str) -> None:
    # Forked from the work-horse: drop the inherited engine so this
    # process opens its own database connection.
    from sigserve import db
    from sigserve.progress import update_progress

    db.get_engine.cache_clear()

    log_path = None
    while True:
        time.sleep(LOG_POLL_SECONDS)
        if log_path is None:
            found = glob.glob(os.path.join(output_dir, "**", "log.txt"), recursive=True)
            if not found:
                continue
            log_path = found[0]
        try:
            with open(log_path) as handle:
                lines = [line.rstrip() for line in handle if line.strip()]
        except OSError:
            continue
        if lines:
            update_progress(job_id, "sampling", log_tail=lines[-LOG_TAIL_LINES:])
