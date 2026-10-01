import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getSharedJob, getSharedResults, isTerminal, rerunJob } from "./api.js";
import { ClassLegend, ExposuresChart, SignatureChart, TraceChart } from "./charts.jsx";
import { downloadFile, exposuresCsv, signaturesCsv } from "./csv.js";
import { formatDuration, formatWhen } from "./time.js";

export default function JobDetailPage({ jobId }) {
  const { data: job, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getSharedJob(jobId),
    refetchInterval: (query) =>
      query.state.data && isTerminal(query.state.data.status) ? false : 2500,
  });

  if (error) {
    return (
      <div className="empty">
        <p>Job not found. It may have been pruned (jobs are kept for 30 days).</p>
        <a href="#/">Submit a new run</a>
      </div>
    );
  }
  if (!job) return <div className="empty">Loading…</div>;

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{job.name || `Job ${job.id.slice(0, 8)}`}</h1>
        <span className={`chip ${job.status}`}>{job.status}</span>
      </div>
      <MetaRow job={job} />
      {job.status === "finished" ? (
        <Results jobId={jobId} job={job} />
      ) : isTerminal(job.status) ? (
        <NotFinished job={job} />
      ) : (
        <Live job={job} />
      )}
    </div>
  );
}

function MetaRow({ job }) {
  const params = job.params ?? {};
  return (
    <div className="meta-row">
      <span>
        submitted <b>{formatWhen(job.created_at)}</b>
      </span>
      {job.n_mutation_types && (
        <span>
          input{" "}
          <b>
            {job.n_mutation_types}×{job.n_samples}
          </b>
        </span>
      )}
      <span>
        rank{" "}
        <b>{params.rank != null ? params.rank : `${params.rank_min}–${params.rank_max}`}</b>
      </span>
      <span>
        max iters <b>{params.max_iters}</b>
      </span>
      <span>
        seed <b>{params.seed ?? "random"}</b>
      </span>
      {params.likelihood && (
        <span>
          model{" "}
          <b>
            {params.likelihood}/{params.prior}
          </b>
        </span>
      )}
    </div>
  );
}

function useElapsed(job) {
  const [, forceTick] = useState(0);
  useEffect(() => {
    if (isTerminal(job.status)) return undefined;
    const timer = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(timer);
  }, [job.status]);
  const start = job.started_at ?? job.created_at;
  if (!start) return null;
  const end = job.finished_at ? new Date(job.finished_at) : new Date();
  return formatDuration((end - new Date(start)) / 1000);
}

function Live({ job }) {
  const elapsed = useElapsed(job);
  return (
    <div>
      {job.status === "queued" ? (
        <div className="ok-box">
          Queued{job.queue_position != null ? ` — position ${job.queue_position} in line` : ""}.
          Waiting for a worker; this page updates automatically.
        </div>
      ) : (
        <div className="ok-box">
          Sampling for <b>{elapsed}</b>. Gibbs sampling takes minutes on real data — leave this
          page open or come back to the same URL.
        </div>
      )}
      {job.progress?.log_tail?.length > 0 && (
        <>
          <h2>Sampler log</h2>
          <div className="log-tail">{job.progress.log_tail.join("\n")}</div>
        </>
      )}
    </div>
  );
}

function RerunButton({ jobId }) {
  const rerun = useMutation({
    mutationFn: () => rerunJob(jobId),
    onSuccess: (job) => {
      window.location.hash = `#/jobs/${job.id}`;
    },
  });
  return (
    <>
      <button className="primary" disabled={rerun.isPending} onClick={() => rerun.mutate()}>
        Re-run with the same settings
      </button>
      {rerun.isError && (
        <div className="error-box">
          {rerun.error.status === 404
            ? "Only the submitting browser can re-run this job."
            : rerun.error.message}
        </div>
      )}
    </>
  );
}

function NotFinished({ job }) {
  return (
    <div>
      {job.status === "failed" ? (
        <div className="error-box">{job.error || "The job failed without a message."}</div>
      ) : (
        <div className="ok-box">This job was canceled.</div>
      )}
      <RerunButton jobId={job.id} />
    </div>
  );
}

const TRACE_METRICS = [
  ["logposterior", "log posterior"],
  ["loglikelihood", "log likelihood"],
  ["bic", "BIC"],
  ["rmse", "RMSE"],
  ["rank", "rank"],
];

function Results({ jobId, job }) {
  const { data, error } = useQuery({
    queryKey: ["results", jobId],
    queryFn: () => getSharedResults(jobId),
  });
  const [metric, setMetric] = useState("logposterior");
  const [copied, setCopied] = useState(false);

  if (error) return <div className="error-box">{error.message}</div>;
  if (!data) return <div className="empty">Loading results…</div>;

  const { signatures, exposures, diagnostics } = data.result;
  const labels = data.labels ?? {};
  const rank = exposures.length;
  const estimatedRank = diagnostics.estimated_rank ?? rank;
  const trace = diagnostics.trace;

  return (
    <div>
      <div className="hero">
        <span className="number">{estimatedRank}</span>
        <span className="label">
          estimated rank
          {diagnostics.rank_min !== diagnostics.rank_max &&
            diagnostics.rank_min != null &&
            ` (searched ${diagnostics.rank_min}–${diagnostics.rank_max})`}
        </span>
      </div>
      <div className="meta-row">
        <span>
          engine <b>{diagnostics.engine}</b>
          {diagnostics.bayesnmf_ref ? ` @ ${diagnostics.bayesnmf_ref.slice(0, 7)}` : ""}
        </span>
        <span>
          converged{" "}
          <b>
            {diagnostics.converged
              ? `yes, at iteration ${diagnostics.converged_at}`
              : `no (hit ${diagnostics.max_iters} iterations)`}
          </b>
        </span>
        {diagnostics.elapsed_seconds != null && (
          <span>
            sampler time <b>{formatDuration(diagnostics.elapsed_seconds)}</b>
          </span>
        )}
      </div>

      <div className="toolbar">
        <button
          onClick={() => downloadFile("signatures.csv", signaturesCsv(signatures, labels.mutation_types))}
        >
          Download signatures
        </button>
        <button
          onClick={() => downloadFile("exposures.csv", exposuresCsv(exposures, labels.sample_names))}
        >
          Download exposures
        </button>
        <button
          onClick={() =>
            downloadFile(
              "run.json",
              JSON.stringify({ id: data.id, name: data.name, params: data.params, diagnostics }, null, 2),
              "application/json"
            )
          }
        >
          Download parameters
        </button>
        <RerunButton jobId={jobId} />
        <button
          className="subtle"
          onClick={() => {
            navigator.clipboard.writeText(window.location.href);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Link copied" : "Copy share link"}
        </button>
      </div>

      <h2>Signature profiles</h2>
      <ClassLegend />
      {Array.from({ length: rank }, (_, k) => (
        <SignatureChart
          key={k}
          title={`Signature ${k + 1}`}
          profile={signatures.map((row) => row[k])}
          mutationTypes={labels.mutation_types}
        />
      ))}

      <ExposuresChart exposures={exposures} sampleNames={labels.sample_names} />

      {trace && (
        <div className="chart-card">
          <div className="toolbar" style={{ margin: 0, justifyContent: "space-between" }}>
            <h3 style={{ margin: 0 }}>Convergence trace</h3>
            <select value={metric} onChange={(event) => setMetric(event.target.value)}>
              {TRACE_METRICS.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <TraceChart trace={trace} metric={metric} />
        </div>
      )}
    </div>
  );
}
