import React from "react";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Play, RefreshCw, ShieldCheck } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import DetailDrawer from "../components/DetailDrawer";
import KPICard from "../components/KPICard";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { useToast } from "../components/ToastProvider";
import { detectionApi } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import { formatAmount, formatNumber } from "../utils/format";

const SEVERITY_COLORS = ["#d95757", "#e1a63b", "#5278dd", "#64748b"];

export default function Detection() {
  const [results, setResults] = useState({ has_run: false, results: [], total_detected: 0, run_at: null });
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const notify = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [latest, counts] = await Promise.all([
        detectionApi.results(),
        detectionApi.summary(),
      ]);
      setResults(latest);
      setSummary(counts);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const run = async () => {
    if (running) return;
    setRunning(true);
    setError("");
    try {
      const latest = await detectionApi.run();
      const counts = await detectionApi.summary();
      setResults(latest);
      setSummary(counts);
      notify(`Detection completed. ${latest.total_detected} findings returned from source transactions.`);
    } catch (runError) {
      setError(runError.message);
      notify(runError.message, "error");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <LoadingState label="Checking the latest detection run…" />;
  const bySeverity = Object.entries(summary?.count_by_severity || {}).map(([name, value]) => ({ name, value }));
  const columns = [
    { key: "anomaly_code", label: "Anomaly type", render: (row) => <span className="anomaly-name">{row.anomaly_code.replaceAll("_", " ")}</span> },
    { key: "entity", label: "Affected entity", render: (row) => <span><span className="entity-type">{row.entity_type}</span> <span className="mono-text">{row.entity_id}</span></span> },
    { key: "expected_value", label: "Expected", numeric: true, render: (row) => typeof row.expected_value === "number" ? formatAmount(row.expected_value) : row.expected_value ?? "—" },
    { key: "actual_value", label: "Actual", numeric: true, render: (row) => typeof row.actual_value === "number" ? formatAmount(row.actual_value) : row.actual_value ?? "—" },
    { key: "variance", label: "Variance", numeric: true, render: (row) => row.variance == null ? "—" : typeof row.variance === "number" ? formatAmount(row.variance) : row.variance },
    { key: "severity", label: "Severity", render: (row) => <StatusBadge value={row.severity} /> },
  ];

  return (
    <div className="page-stack">
      <div className="detection-hero">
        <div className="detection-hero-icon"><ShieldCheck size={25} /></div>
        <div className="detection-hero-copy"><span className="eyebrow">SOURCE TRANSACTION ANALYSIS</span><h2>Independent anomaly detection</h2><p>Run seven rule-based checks against order, shipment, invoice, payment, dispute, and lifecycle records.</p></div>
        <button className="button button-primary run-button" onClick={run} disabled={running}>
          {running ? <RefreshCw className="spin" size={17} /> : <Play size={16} fill="currentColor" />}
          {running ? "Detection running…" : "Run detection"}
        </button>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      {running && <div className="progress-banner"><span className="spinner-small" />Analyzing live transaction data. This can take a few seconds…</div>}
      {!results.has_run && !running && (
        <div className="notice-card"><AlertTriangle size={18} /><div><strong>No detection run in this server session</strong><span>Start a run to analyze the current MySQL transaction data. Results are not persisted between backend restarts.</span></div></div>
      )}
      <div className="kpi-grid detection-kpis">
        <KPICard label="Findings in latest run" value={formatNumber(summary?.total_detected_anomalies || 0)} caption={summary?.run_at ? `Run ${new Date(summary.run_at).toLocaleString()}` : "No run yet"} icon={AlertTriangle} tone="navy" />
        <KPICard label="Estimated exposure" value={formatAmount(summary?.estimated_revenue_leakage || 0)} caption="Rule-level estimated financial impact" icon={ShieldCheck} tone="red" />
        <KPICard label="High severity" value={formatNumber(summary?.count_by_severity?.HIGH || 0)} caption="Findings requiring attention" icon={AlertTriangle} tone="amber" />
        <KPICard label="Rule categories active" value={formatNumber(Object.keys(summary?.count_by_anomaly_type || {}).length)} caption="Categories with findings" icon={CheckCircle2} tone="green" />
      </div>
      <div className="dashboard-chart-grid">
        <ChartCard title="Findings by anomaly category" description="Number of findings independently returned by each detection rule." className="chart-wide">
          {Object.keys(summary?.count_by_anomaly_type || {}).length ? (
            <div className="category-count-list">
              {Object.entries(summary.count_by_anomaly_type).map(([code, count]) => <div key={code} className="category-count-row"><span className="anomaly-bullet" /><span>{code.replaceAll("_", " ")}</span><strong>{count}</strong></div>)}
            </div>
          ) : <EmptyState title="No findings to summarize" message="Run detection to populate this view." />}
        </ChartCard>
        <ChartCard title="Severity distribution" description="Severity classification of findings in the latest run.">
          <div className="chart-area chart-area-short">
            {bySeverity.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={bySeverity} dataKey="value" nameKey="name" innerRadius={58} outerRadius={88} paddingAngle={4}>{bySeverity.map((item, index) => <Cell key={item.name} fill={SEVERITY_COLORS[index % SEVERITY_COLORS.length]} />)}</Pie><Tooltip formatter={(value, name) => [value, name]} /></PieChart></ResponsiveContainer> : <EmptyState title="No severity data" />}
          </div>
          <div className="severity-legend">{bySeverity.map((item, index) => <span key={item.name}><i style={{ background: SEVERITY_COLORS[index % SEVERITY_COLORS.length] }} />{item.name}<strong>{item.value}</strong></span>)}</div>
        </ChartCard>
      </div>
      <section className="section-block">
        <div className="section-heading"><div><h3>Detection results</h3><p>Findings returned from original transaction tables—not copied from the exception register.</p></div></div>
        <DataTable columns={columns} rows={results.results || []} onView={(row) => setDetail({ open: true, title: `${row.anomaly_code.replaceAll("_", " ")} · ${row.entity_id}`, data: row })} emptyTitle="No detection results yet" />
      </section>
      <DetailDrawer open={detail?.open} title={detail?.title || "Finding details"} data={detail?.data} onClose={() => setDetail(null)} />
    </div>
  );
}
