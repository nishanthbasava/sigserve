import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelJob, isTerminal, listJobs } from "./api.js";
import { formatWhen, runtimeOf } from "./time.js";

export default function JobsPage() {
  const queryClient = useQueryClient();
  const { data: jobs, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    // Poll fast while anything is active, slowly otherwise.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((job) => !isTerminal(job.status)) ? 3000 : 15000,
  });

  const cancel = useMutation({
    mutationFn: cancelJob,
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  if (isLoading) return <div className="empty">Loading jobs…</div>;
  if (error) return <div className="error-box">{error.message}</div>;

  if (!jobs || jobs.length === 0) {
    return (
      <div className="empty">
        <p>No runs yet.</p>
        <a href="#/">Submit your first dataset</a>
      </div>
    );
  }

  return (
    <div>
      <h1>Jobs</h1>
      <p className="subtitle">
        Runs from this browser. Open one for live status, plots, and downloads — the page URL is
        shareable.
      </p>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Dataset</th>
            <th>Status</th>
            <th>Submitted</th>
            <th className="num">Runtime</th>
            <th className="num">Samples</th>
            <th className="num">Rank</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              className="clickable"
              onClick={() => {
                window.location.hash = `#/jobs/${job.id}`;
              }}
            >
              <td className="mono" title={job.id}>
                {job.id.slice(0, 8)}
              </td>
              <td>{job.name || "—"}</td>
              <td>
                <span className={`chip ${job.status}`}>{job.status}</span>
              </td>
              <td title={job.created_at}>{formatWhen(job.created_at)}</td>
              <td className="num">{runtimeOf(job) ?? "—"}</td>
              <td className="num" title={job.n_mutation_types ? `${job.n_mutation_types} mutation types` : undefined}>
                {job.n_samples ?? "—"}
              </td>
              <td className="num">{rankLabel(job.params)}</td>
              <td className="num">
                {!isTerminal(job.status) && (
                  <button
                    className="subtle"
                    onClick={(event) => {
                      event.stopPropagation();
                      cancel.mutate(job.id);
                    }}
                  >
                    cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function rankLabel(params) {
  if (!params) return "—";
  if (params.rank != null) return String(params.rank);
  if (params.rank_min != null) return `${params.rank_min}–${params.rank_max}`;
  return "—";
}
