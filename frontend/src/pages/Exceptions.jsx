import React from "react";
import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Download, Search } from "lucide-react";
import DataTable from "../components/DataTable";
import DetailDrawer from "../components/DetailDrawer";
import { ErrorState, LoadingState } from "../components/PageState";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { downloadCsv, exceptionApi } from "../services/api";
import { formatAmount } from "../utils/format";

const anomalyTypes = [
  "PRICE_VARIANCE",
  "SHIPMENT_QUANTITY",
  "BILLING_MISMATCH",
  "CASH_APPLICATION",
  "DISPUTE_LEAKAGE",
  "ORDER_CLOSED_UNPAID",
  "STATUS_TRANSITION_SKIP",
];
const exceptionStatuses = ["OPEN", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"];

function affectedEntity(row) {
  if (row.sales_order_id) return `Order · ${row.sales_order_id}`;
  if (row.invoice_id) return `Invoice · ${row.invoice_id}`;
  if (row.payment_id) return `Payment · ${row.payment_id}`;
  if (row.dispute_id) return `Dispute · ${row.dispute_id}`;
  if (row.shipment_id) return `Shipment · ${row.shipment_id}`;
  if (row.account_id) return `Account · ${row.account_id}`;
  return row.exception_id;
}

export default function Exceptions() {
  const [filters, setFilters] = useState({ anomaly_code: "", status: "", search: "" });
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ items: [], pagination: null });
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [updating, setUpdating] = useState("");
  const notify = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [list, counts] = await Promise.all([
        exceptionApi.list({
          ...filters,
          page,
          per_page: 15,
          sort_by: "detected_at",
          sort_order: "desc",
        }),
        exceptionApi.summary(),
      ]);
      setResult(list);
      setSummary(counts);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { load(); }, [load]);

  const updateFilter = (key, value) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };
  const openDetail = async (row) => {
    setDetail({ open: true, title: row.exception_id, data: null, id: row.exception_id });
    setDetailLoading(true);
    setDetailError("");
    try {
      const [record, source] = await Promise.all([
        exceptionApi.get(row.exception_id),
        exceptionApi.source(row.exception_id),
      ]);
      setDetail((current) => ({ ...current, data: { ...record, source_records: source } }));
    } catch (detailRequestError) {
      setDetailError(detailRequestError.message);
    } finally {
      setDetailLoading(false);
    }
  };
  const updateStatus = async (row, status) => {
    setUpdating(row.exception_id);
    try {
      await exceptionApi.updateStatus(row.exception_id, status);
      notify(`${row.exception_id} status updated to ${status.replaceAll("_", " ")}.`);
      await load();
      if (detail?.id === row.exception_id) await openDetail({ ...row });
    } catch (updateError) {
      notify(updateError.message, "error");
    } finally {
      setUpdating("");
    }
  };

  const columns = [
    { key: "exception_id", label: "Exception ID", render: (row) => <span className="mono-text">{row.exception_id}</span> },
    { key: "anomaly_code", label: "Anomaly type", render: (row) => <span className="anomaly-name">{row.anomaly_code?.replaceAll("_", " ")}</span> },
    { key: "entity", label: "Affected entity", render: (row) => <span className="secondary-cell">{affectedEntity(row)}</span> },
    { key: "variance_amount", label: "Variance", numeric: true, render: (row) => row.variance_amount != null ? <span className="amount-value">{formatAmount(row.variance_amount)}</span> : row.actual_amount != null ? formatAmount(Number(row.actual_amount) - Number(row.expected_amount || 0)) : "—" },
    { key: "severity", label: "Severity", render: (row) => <StatusBadge value={row.severity} /> },
    { key: "status", label: "Status", render: (row) => (
      <select className="status-select" value={row.status} disabled={updating === row.exception_id} aria-label={`Update status for ${row.exception_id}`} onClick={(event) => event.stopPropagation()} onChange={(event) => updateStatus(row, event.target.value)}>
        {exceptionStatuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
      </select>
    ) },
    { key: "detected_at", label: "Detected", render: (row) => row.detected_at ? new Date(row.detected_at).toLocaleDateString() : "—" },
  ];

  const exportRows = () => {
    try {
      downloadCsv("exceptions.csv", result.items, [
        { label: "Exception ID", value: (row) => row.exception_id },
        { label: "Anomaly type", value: (row) => row.anomaly_code },
        { label: "Affected entity", value: affectedEntity },
        { label: "Variance", value: (row) => row.variance_amount ?? (row.actual_amount != null ? Number(row.actual_amount) - Number(row.expected_amount || 0) : "") },
        { label: "Severity", value: (row) => row.severity },
        { label: "Status", value: (row) => row.status },
        { label: "Detected at", value: (row) => row.detected_at },
      ]);
    } catch (exportError) { notify(exportError.message, "error"); }
  };

  return (
    <div className="page-stack">
      <div className="page-heading-row"><div><span className="eyebrow">RISK & CONTROL</span><h2>Exception management</h2><p>Investigate data issues and track resolution across the order-to-cash process.</p></div><button className="button button-secondary" onClick={exportRows} disabled={!result.items.length}><Download size={16} />Export CSV</button></div>
      <div className="exception-summary-strip">
        <div className="summary-intro"><span className="summary-icon"><AlertCircle size={19} /></span><div><strong>{summary?.total_exceptions?.toLocaleString() ?? "—"}</strong><span>Exceptions in register</span></div></div>
        {Object.entries(summary?.count_by_anomaly_type || {}).slice(0, 7).map(([code, count]) => <div className="summary-chip" key={code}><span>{code.replaceAll("_", " ")}</span><strong>{count}</strong></div>)}
      </div>
      <div className="filter-bar">
        <label className="search-field filter-search"><Search size={16} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Search ID, order, invoice, account" /></label>
        <label className="select-filter"><span>Anomaly type</span><select value={filters.anomaly_code} onChange={(event) => updateFilter("anomaly_code", event.target.value)}><option value="">All anomaly types</option>{anomalyTypes.map((code) => <option key={code} value={code}>{code.replaceAll("_", " ")}</option>)}</select></label>
        <label className="select-filter"><span>Status</span><select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All statuses</option>{exceptionStatuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
      </div>
      {error && !result.items.length ? <ErrorState message={error} onRetry={load} /> : loading && !result.items.length ? <LoadingState label="Loading exception register…" /> : (
        <DataTable columns={columns} rows={result.items} loading={loading} pagination={result.pagination} onPageChange={setPage} onView={openDetail} emptyTitle="No exceptions match these filters" />
      )}
      <DetailDrawer open={detail?.open} title={detail?.title || "Exception details"} data={detail?.data} loading={detailLoading} error={detailError} onClose={() => setDetail(null)} />
    </div>
  );
}