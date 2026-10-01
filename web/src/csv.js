// CSV parsing, validation, and export helpers.
//
// Upload orientation is samples x contexts (one row per sample, one
// column per trinucleotide context); the API wants the transpose
// (contexts x samples), so the parser hands back the transposed matrix
// plus the labels for both axes.

import Papa from "papaparse";

export const SUBSTITUTIONS = ["C>A", "C>G", "C>T", "T>A", "T>C", "T>G"];
const BASES = ["A", "C", "G", "T"];

export const CONTEXTS_96 = SUBSTITUTIONS.flatMap((sub) =>
  BASES.flatMap((five) => BASES.map((three) => `${five}[${sub}]${three}`))
);

const CONTEXT_RE = /^[ACGT]\[[ACGT]>[ACGT]\][ACGT]$/;

export function substitutionOf(context) {
  return context.slice(2, 5);
}

export class CsvError extends Error {}

export function parseMatrixCsv(text) {
  const { data } = Papa.parse(text.trim(), { skipEmptyLines: "greedy" });
  if (data.length < 2) {
    throw new CsvError("The file needs a header row of contexts plus at least one sample row.");
  }

  const header = data[0].map((cell) => String(cell).trim());
  const hasIdColumn = !CONTEXT_RE.test(header[0]);
  const contextHeader = hasIdColumn ? header.slice(1) : header;

  const invalid = contextHeader.filter((label) => !CONTEXT_RE.test(label));
  if (invalid.length > 0) {
    throw new CsvError(
      `The header must name trinucleotide contexts like A[C>A]A. ` +
        `${invalid.length} column header(s) do not match, starting with "${invalid[0]}".`
    );
  }
  if (contextHeader.length !== 96) {
    throw new CsvError(
      `Expected 96 context columns (one per trinucleotide context); found ${contextHeader.length}.`
    );
  }
  const seen = new Set(contextHeader);
  if (seen.size !== 96 || CONTEXTS_96.some((context) => !seen.has(context))) {
    throw new CsvError(
      "The 96 context columns must cover every trinucleotide context exactly once."
    );
  }
  // Column order in the file may differ from canonical; map it.
  const order = CONTEXTS_96.map((context) => contextHeader.indexOf(context));

  const sampleNames = [];
  const rows = [];
  const problems = [];
  for (let r = 1; r < data.length; r += 1) {
    const raw = data[r].map((cell) => String(cell).trim());
    const name = hasIdColumn ? raw[0] : `sample_${r}`;
    const values = hasIdColumn ? raw.slice(1) : raw;
    if (values.length !== 96) {
      problems.push(`row ${r + 1} ("${name}") has ${values.length} values, expected 96`);
      continue;
    }
    const parsed = new Array(96);
    for (let c = 0; c < 96; c += 1) {
      const cell = values[c];
      if (!/^\d+$/.test(cell)) {
        problems.push(
          `row ${r + 1} ("${name}"), column ${contextHeader[c]}: "${cell}" is not a ` +
            `non-negative integer count`
        );
        break;
      }
      parsed[c] = Number(cell);
    }
    if (parsed.includes(undefined)) continue;
    sampleNames.push(name);
    rows.push(order.map((index) => parsed[index]));
    if (problems.length >= 5) break;
  }

  if (problems.length > 0) {
    throw new CsvError(`The file has non-count values:\n${problems.slice(0, 5).join("\n")}`);
  }
  if (rows.length === 0) throw new CsvError("No sample rows found.");
  if (rows.length > 2000) throw new CsvError("At most 2000 samples are supported.");

  // Transpose samples x contexts -> contexts x samples.
  const matrix = CONTEXTS_96.map((_, i) => rows.map((row) => row[i]));
  return { matrix, mutationTypes: [...CONTEXTS_96], sampleNames };
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv(rows) {
  return rows.map((row) => row.map(csvEscape).join(",")).join("\n") + "\n";
}

export function downloadFile(filename, content, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function signaturesCsv(signatures, mutationTypes) {
  const rank = signatures[0]?.length ?? 0;
  const header = ["context", ...Array.from({ length: rank }, (_, k) => `signature_${k + 1}`)];
  const rows = signatures.map((row, i) => [mutationTypes?.[i] ?? `type_${i + 1}`, ...row]);
  return toCsv([header, ...rows]);
}

export function exposuresCsv(exposures, sampleNames) {
  const header = ["signature", ...(sampleNames ?? exposures[0].map((_, j) => `sample_${j + 1}`))];
  const rows = exposures.map((row, k) => [`signature_${k + 1}`, ...row]);
  return toCsv([header, ...rows]);
}
