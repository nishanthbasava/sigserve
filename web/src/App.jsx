import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getMeta } from "./api.js";
import JobDetailPage from "./JobDetailPage.jsx";
import JobsPage from "./JobsPage.jsx";
import SubmitPage from "./SubmitPage.jsx";

function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHashRoute();
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: getMeta, staleTime: Infinity });

  const jobMatch = hash.match(/^#\/jobs\/([A-Za-z0-9-]+)/);
  let page;
  if (jobMatch) page = <JobDetailPage jobId={jobMatch[1]} />;
  else if (hash.startsWith("#/jobs")) page = <JobsPage />;
  else page = <SubmitPage />;

  const active = jobMatch || hash.startsWith("#/jobs") ? "jobs" : "submit";

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          SigServe
        </a>
        <nav>
          <a className={active === "submit" ? "active" : ""} href="#/">
            Submit
          </a>
          <a className={active === "jobs" ? "active" : ""} href="#/jobs">
            Jobs
          </a>
          <a href="/api/docs" target="_blank" rel="noreferrer">
            API
          </a>
        </nav>
        <span className="version">{meta ? `v${meta.version}` : ""}</span>
      </header>
      <main>{page}</main>
      <footer className="footer">
        Bayesian NMF mutational-signature analysis via{" "}
        <a href="https://github.com/jennalandy/bayesNMF" target="_blank" rel="noreferrer">
          bayesNMF
        </a>
        . Jobs are pruned after 30 days.
      </footer>
    </div>
  );
}
