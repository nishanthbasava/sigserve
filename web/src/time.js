export function formatWhen(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  const deltaSeconds = (Date.now() - date.getTime()) / 1000;
  if (deltaSeconds < 60) return "just now";
  if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)} min ago`;
  if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)} h ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return null;
  const whole = Math.max(0, Math.round(seconds));
  if (whole < 60) return `${whole}s`;
  const minutes = Math.floor(whole / 60);
  if (minutes < 60) return `${minutes}m ${whole % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function runtimeOf(job) {
  if (!job.started_at) return null;
  const end = job.finished_at ? new Date(job.finished_at) : new Date();
  return formatDuration((end - new Date(job.started_at)) / 1000);
}
