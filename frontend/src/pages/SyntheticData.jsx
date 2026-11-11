import React from "react";
import { useEffect, useState } from "react";
import { Database, FlaskConical, RefreshCw, ShieldCheck } from "lucide-react";
import { ErrorState } from "../components/PageState";
import { useToast } from "../components/ToastProvider";
import { syntheticDataApi } from "../services/api";

const isRunning = (job) => job && ["queued", "running"].includes(job.status);

export default function SyntheticData() {
  const [profile, setProfile] = useState("small");
  const [job, setJob] = useState(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const notify = useToast();

  useEffect(() => {
    if (!isRunning(job)) return undefined;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const updated = await syntheticDataApi.getJob(job.job_id);
        if (active) {
          setJob(updated);
          if (updated.status === "completed") notify("Sandbox dataset generated successfully.", "success");
          if (updated.status === "failed") notify(updated.message, "error");
        }
      } catch (requestError) {
        if (active) setError(requestError.message);
      }
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [job?.job_id, job?.status, notify]);

  const start = async () => {
    setStarting(true);
    setError("");
    try {
      setJob(await syntheticDataApi.start(profile));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setStarting(false);
    }
  };

  const refresh = async () => {
    if (!job?.job_id) return;
    try {
      setJob(await syntheticDataApi.getJob(job.job_id));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <div className="page-stack">
      <div className="page-heading-row">
        <div><span className="eyebrow">DEVELOPMENT & QA</span><h2>Synthetic data generator</h2><p>Create a realistic, relational O2C dataset in a dedicated MySQL sandbox.</p></div>
      </div>
      <section className="content-card generator-card">
        <div className="generator-safety"><ShieldCheck size={19} /><div><strong>Isolated by design</strong><span>Generation creates a new sandbox database. It does not write to the configured application database or seeded ground-truth records.</span></div></div>
        <label className="form-field" htmlFor="generator-profile">
          <span>Dataset size</span>
          <select id="generator-profile" value={profile} onChange={(event) => setProfile(event.target.value)} disabled={starting || isRunning(job)}>
            <option value="small">Small — quick local testing</option>
            <option value="demo">Demo — fuller dataset</option>
          </select>
        </label>
        <div className="generator-actions">
          <button className="button button-primary" onClick={start} disabled={starting || isRunning(job)}>
            {isRunning(job) ? <RefreshCw size={16} className="spin" /> : <FlaskConical size={16} />}
            {starting ? "Starting…" : isRunning(job) ? "Generation in progress" : "Generate sandbox dataset"}
          </button>
          {job && <button className="button button-secondary" onClick={refresh}><RefreshCw size={15} />Refresh status</button>}
        </div>
        {error && <ErrorState message={error} onRetry={refresh} />}
      </section>
      {job && (
        <section className="content-card">
          <div className="section-heading"><div><h3>Generation status</h3><p>{job.message}</p></div><span className={`status-badge status-${job.status}`}>{job.status}</span></div>
          {job.database && <div className="sandbox-database"><Database size={16} /><span>Sandbox database</span><code>{job.database}</code></div>}
          {job.tables && <div className="sandbox-tables">{Object.entries(job.tables).map(([table, count]) => <div key={table}><span>{table.replaceAll("_", " ")}</span><strong>{count.toLocaleString()}</strong></div>)}</div>}
          {job.status === "completed" && <p className="muted-copy">The application remains connected to its configured database. To browse this sandbox, start a separate backend using this database name as `DB_NAME`.</p>}
          {job.output_directory && <p className="muted-copy">Run output: <code>{job.output_directory}</code></p>}
        </section>
      )}
      <section className="content-card"><h3>Before you generate</h3><p className="muted-copy">The sandbox schema is created using only CREATE TABLE and append-only trigger statements from the project schema. No DROP statements run. Generated sandbox databases are retained for review; remove a sandbox only through an explicit database administrator action.</p></section>
    </div>
  );
}
