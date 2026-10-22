import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { submitJob } from "./api.js";
import { parseMatrixCsv } from "./csv.js";
import SbsPlot from "./SbsPlot.jsx";

const DEFAULTS = {
  rankMin: 2,
  rankMax: 8,
  maxIters: 2000,
  seed: "",
  fixedRank: "",
  likelihood: "poisson",
  prior: "truncnormal",
};

const curlExample = (origin) => `# mint an API key
curl -sX POST ${origin}/api/keys -H 'Content-Type: application/json' -d '{}'

# submit: matrix rows are mutation types, columns are samples
curl -sX POST ${origin}/api/jobs \\
  -H 'Content-Type: application/json' -H "X-API-Key: $KEY" \\
  -d '{"matrix": [[12,3],[5,8],[9,1]], "params": {"rank": 2, "max_iters": 2000}}'

# poll status, then fetch results (409 until finished)
curl -s ${origin}/api/jobs/$JOB -H "X-API-Key: $KEY"
curl -s ${origin}/api/jobs/$JOB/results -H "X-API-Key: $KEY"`;

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="copy-button"
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

// First rows and columns of the bundled sample CSV, so the expected file
// format is shown with real values rather than described in prose.
function CsvPreview() {
  const { data } = useQuery({
    queryKey: ["sample-csv"],
    queryFn: async () => (await fetch("/sample-dataset.csv")).text(),
    staleTime: Infinity,
  });
  if (!data) return null;
  const rows = data.trim().split("\n").slice(0, 4).map((line) => line.split(","));
  const nColumns = 5;
  return (
    <div className="csv-preview">
      <table>
        <thead>
          <tr>
            {rows[0].slice(0, nColumns).map((cell) => (
              <th key={cell}>{cell}</th>
            ))}
            <th className="ellipsis">… 96 context columns</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row) => (
            <tr key={row[0]}>
              {row.slice(0, nColumns).map((cell, index) => (
                <td key={index}>{cell}</td>
              ))}
              <td className="ellipsis">…</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// The sample dataset's planted ground truth, rendered with the same plot
// component the results page uses.
function ExampleOutput() {
  const { data } = useQuery({
    queryKey: ["sample-signatures"],
    queryFn: async () => {
      const response = await fetch("/sample-signatures.json");
      if (!response.ok) throw new Error("sample signatures unavailable");
      return response.json();
    },
    staleTime: Infinity,
  });
  if (!data) return null;
  return (
    <>
      {data.signatures.map((signature) => (
        <SbsPlot
          key={signature.name}
          title={signature.name}
          profile={signature.profile}
          contexts={data.contexts}
          plotHeight={110}
          showContextLabels={false}
          labelScale={2}
        />
      ))}
    </>
  );
}

export default function SubmitPage() {
  const [dataset, setDataset] = useState(null); // {matrix, mutationTypes, sampleNames, source}
  const [parseError, setParseError] = useState(null);
  const [name, setName] = useState("");
  const [params, setParams] = useState(DEFAULTS);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);
  const loadedRef = useRef(null);

  // The parameters form renders below the fold, so a successful load looked
  // like nothing happened. Bring the confirmation into view.
  useEffect(() => {
    if (dataset) loadedRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [dataset]);

  const submit = useMutation({
    mutationFn: submitJob,
    onSuccess: (job) => {
      window.location.hash = `#/jobs/${job.id}`;
    },
  });

  async function loadText(text, source) {
    try {
      const parsed = parseMatrixCsv(text);
      setDataset({ ...parsed, source });
      setParseError(null);
      if (!name) setName(source.replace(/\.csv$/i, ""));
    } catch (error) {
      setDataset(null);
      setParseError(error.message);
    }
  }

  async function onFile(file) {
    if (!file) return;
    await loadText(await file.text(), file.name);
  }

  async function loadSample() {
    const response = await fetch("/sample-dataset.csv");
    await loadText(await response.text(), "sample-dataset");
    setName("Sample dataset");
  }

  const nSamples = dataset?.sampleNames.length ?? 0;
  const maxRank = Math.min(96, nSamples);
  const fixedRank = params.fixedRank === "" ? null : Number(params.fixedRank);
  const effectiveMax = fixedRank ?? Number(params.rankMax);
  const rankProblem =
    dataset &&
    (effectiveMax > maxRank
      ? `Rank ${effectiveMax} exceeds the smaller matrix dimension (${maxRank}).`
      : fixedRank === null && Number(params.rankMin) > Number(params.rankMax)
        ? "Rank min must not exceed rank max."
        : null);

  function startRun() {
    submit.mutate({
      matrix: dataset.matrix,
      name: name || null,
      mutation_types: dataset.mutationTypes,
      sample_names: dataset.sampleNames,
      params: {
        rank: fixedRank,
        rank_min: Number(params.rankMin),
        rank_max: Number(params.rankMax),
        max_iters: Number(params.maxIters),
        seed: params.seed === "" ? null : Number(params.seed),
        likelihood: params.likelihood,
        prior: params.prior,
      },
    });
  }

  const set = (key) => (event) => setParams({ ...params, [key]: event.target.value });
  const curl = curlExample(window.location.origin);

  return (
    <div>
      <div className="landing-grid">
        <section>
          <h1>Mutational signatures from a CSV of mutation counts</h1>
          <p className="subtitle">
            Upload one row per sample and one column per trinucleotide context (96 columns). Runs
            the bayesNMF Gibbs sampler server-side. Returns signatures, exposures, and posterior
            rank.
          </p>

          <div
            className={`dropzone ${dragging ? "dragging" : ""}`}
            onClick={() => fileInput.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              onFile(event.dataTransfer.files[0]);
            }}
          >
            <strong>Drop a CSV here</strong> or click to browse
            <div className="hint">
              samples &times; 96 contexts, integer counts, header row required
            </div>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(event) => onFile(event.target.files[0])}
            />
          </div>

          <div className="sample-row">
            No data handy?
            <button type="button" onClick={loadSample}>
              Try the sample dataset
            </button>
            <span className="note">30 synthetic samples with 3 planted signatures</span>
          </div>

          {parseError && <div className="error-box">{parseError}</div>}

          <h2>Expected file format</h2>
          <CsvPreview />

          <h2>Or use the API directly</h2>
          <div className="curl-block">
            <CopyButton text={curl} />
            <pre>{curl}</pre>
          </div>
          <p className="note">
            Full schema and every endpoint at{" "}
            <a href="/api/docs" target="_blank" rel="noreferrer">
              /api/docs
            </a>
            . Keys are rate-limited per IP; jobs per key.
          </p>
        </section>

        <section>
          <h2 className="column-title">What a run returns</h2>
          <p className="subtitle">
            The three signatures planted in the bundled sample dataset, drawn with the same plot
            the results page uses. A run on that dataset should recover these profiles, their
            per-sample exposures, and a learned rank of 3.
          </p>
          <ExampleOutput />
        </section>
      </div>

      {dataset && (
        <>
          <div className="ok-box" ref={loadedRef}>
            Loaded <b>{dataset.source}</b>: {nSamples} samples &times; 96 contexts,{" "}
            {dataset.matrix.flat().reduce((a, b) => a + b, 0).toLocaleString()} total mutations.
          </div>

          <h2>Parameters</h2>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="name">Dataset name</label>
              <input
                id="name"
                style={{ width: 220 }}
                value={name}
                maxLength={200}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="rank-min">Rank range</label>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  id="rank-min"
                  type="number"
                  min="1"
                  max="20"
                  style={{ width: 62 }}
                  value={params.rankMin}
                  disabled={fixedRank !== null}
                  onChange={set("rankMin")}
                />
                &ndash;
                <input
                  aria-label="Rank max"
                  type="number"
                  min="1"
                  max="20"
                  style={{ width: 62 }}
                  value={params.rankMax}
                  disabled={fixedRank !== null}
                  onChange={set("rankMax")}
                />
              </div>
              <span className="note">the best rank in this range is learned (SBFI)</span>
            </div>
            <div className="field">
              <label htmlFor="iters">Max iterations</label>
              <input
                id="iters"
                type="number"
                min="100"
                max="20000"
                step="100"
                value={params.maxIters}
                onChange={set("maxIters")}
              />
              <span className="note">2000 is a sensible default</span>
            </div>
            <div className="field">
              <label htmlFor="seed">Seed</label>
              <input
                id="seed"
                type="number"
                min="0"
                placeholder="random"
                value={params.seed}
                onChange={set("seed")}
              />
              <span className="note">seeds R's RNG for an exactly repeatable run</span>
            </div>
          </div>

          <details className="advanced">
            <summary>Advanced</summary>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="fixed-rank">Fixed rank</label>
                <input
                  id="fixed-rank"
                  type="number"
                  min="1"
                  max="20"
                  placeholder="learn it"
                  value={params.fixedRank}
                  onChange={set("fixedRank")}
                />
                <span className="note">overrides the range</span>
              </div>
              <div className="field">
                <label htmlFor="likelihood">Likelihood</label>
                <select id="likelihood" value={params.likelihood} onChange={set("likelihood")}>
                  <option value="poisson">poisson</option>
                  <option value="normal">normal</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="prior">Prior</label>
                <select id="prior" value={params.prior} onChange={set("prior")}>
                  <option value="truncnormal">truncnormal</option>
                  <option value="exponential">exponential</option>
                  <option value="gamma">gamma</option>
                </select>
              </div>
            </div>
          </details>

          {rankProblem && <div className="error-box">{rankProblem}</div>}
          {submit.isError && <div className="error-box">{submit.error.message}</div>}

          <button
            className="primary"
            disabled={Boolean(rankProblem) || submit.isPending}
            onClick={startRun}
          >
            {submit.isPending ? "Submitting…" : "Run bayesNMF"}
          </button>
        </>
      )}
    </div>
  );
}
