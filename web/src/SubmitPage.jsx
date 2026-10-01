import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { submitJob } from "./api.js";
import { parseMatrixCsv } from "./csv.js";

const DEFAULTS = {
  rankMin: 2,
  rankMax: 8,
  maxIters: 2000,
  seed: "",
  fixedRank: "",
  likelihood: "poisson",
  prior: "truncnormal",
};

export default function SubmitPage() {
  const [dataset, setDataset] = useState(null); // {matrix, mutationTypes, sampleNames, source}
  const [parseError, setParseError] = useState(null);
  const [name, setName] = useState("");
  const [params, setParams] = useState(DEFAULTS);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);

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

  return (
    <div>
      <h1>Run bayesNMF on your mutation counts</h1>
      <p className="subtitle">
        Upload a CSV with one row per sample and one column per trinucleotide context (96
        columns). Sampling runs on our workers — no R, no install.
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
        <div className="hint">samples &times; 96 contexts, integer counts, header row required</div>
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

      {dataset && (
        <>
          <div className="ok-box">
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
              <span className="note">the best rank in this range is learned</span>
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
              <span className="note">set for a repeatable run</span>
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
