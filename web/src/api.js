// API client. Authenticated calls use a per-browser key, minted
// self-serve on first use and kept in localStorage so each visitor sees
// only their own jobs. Job detail pages use the unauthenticated
// /shared/* reads so result URLs work for anyone they are sent to.

const KEY_STORAGE = "sigserve_api_key";

export class ApiError extends Error {
  constructor(status, detail) {
    super(formatDetail(detail) || `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => entry.msg || JSON.stringify(entry))
      .join("; ")
      .replace(/Value error, /g, "");
  }
  return detail ? JSON.stringify(detail) : "";
}

async function parseError(response) {
  let detail = null;
  try {
    detail = (await response.json()).detail;
  } catch {
    // Non-JSON error body; status alone will have to do.
  }
  return new ApiError(response.status, detail);
}

async function mintKey() {
  const response = await fetch("/api/keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok) throw await parseError(response);
  const body = await response.json();
  localStorage.setItem(KEY_STORAGE, body.key);
  return body.key;
}

async function authedFetch(path, options = {}, retry = true) {
  let key = localStorage.getItem(KEY_STORAGE);
  if (!key) key = await mintKey();

  const headers = { "X-API-Key": key, ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, { ...options, headers });

  if (response.status === 401 && retry) {
    // Stale key (e.g. pruned server-side): mint a fresh one and retry once.
    localStorage.removeItem(KEY_STORAGE);
    return authedFetch(path, options, false);
  }
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function publicFetch(path) {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

export const listJobs = () => authedFetch("/jobs");
export const submitJob = (payload) =>
  authedFetch("/jobs", { method: "POST", body: JSON.stringify(payload) });
export const rerunJob = (id) => authedFetch(`/jobs/${id}/rerun`, { method: "POST" });
export const cancelJob = (id) => authedFetch(`/jobs/${id}`, { method: "DELETE" });

export const getSharedJob = (id) => publicFetch(`/shared/jobs/${id}`);
export const getSharedResults = (id) => publicFetch(`/shared/jobs/${id}/results`);
export const getMeta = () => publicFetch("/meta");

export const TERMINAL_STATUSES = ["finished", "failed", "canceled"];
export const isTerminal = (status) => TERMINAL_STATUSES.includes(status);
