import React from "react";
import { useEffect, useState } from "react";
import { NavLink, Navigate, useParams } from "react-router-dom";
import { CalendarDays, Plus, RotateCcw, Search } from "lucide-react";
import DataTable from "../components/DataTable";
import DetailDrawer from "../components/DetailDrawer";
import { ErrorState, LoadingState } from "../components/PageState";
import { useToast } from "../components/ToastProvider";
import RecordEditor from "../components/RecordEditor";
import { capabilityApi, downloadCsv, transactionApi } from "../services/api";
import { TRANSACTION_RESOURCES, useTransactionResource } from "./Quotes";

const resourceKeys = Object.keys(TRANSACTION_RESOURCES);

function ResourceTable({ resource, config, writesEnabled }) {
  const { result, loading, error, filters, setFilters, page, setPage, load } = useTransactionResource(resource);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [editor, setEditor] = useState({ open: false, record: null });
  const notify = useToast();

  const updateFilter = (key, value) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };
  const viewRecord = async (row) => {
    const recordId = row[config.id];
    setDetail({ open: true, title: recordId, data: null });
    setDetailLoading(true);
    setDetailError("");
    try {
      const record = await transactionApi.get(config.path, recordId);
      setDetail((current) => ({ ...current, data: record }));
    } catch (requestError) {
      setDetailError(requestError.message);
    } finally {
      setDetailLoading(false);
    }
  };
  const editRecord = async (row) => {
    try {
      const fullRecord = await transactionApi.get(config.path, row[config.id]);
      setEditor({ open: true, record: fullRecord });
    } catch (requestError) {
      notify(requestError.message, "error");
    }
  };
  const saveRecord = async (payload) => {
    try {
      if (editor.record) {
        await transactionApi.update(resource, editor.record[config.id], payload);
        notify("Transaction record updated.", "success");
      } else {
        await transactionApi.create(resource, payload);
        notify("Transaction record created.", "success");
      }
      setEditor({ open: false, record: null });
      await load();
    } catch (requestError) {
      throw requestError;
    }
  };
  const removeRecord = async (row) => {
    if (!window.confirm(`Permanently delete ${row[config.id]}? Related records may prevent deletion.`)) return;
    try {
      await transactionApi.delete(resource, row[config.id]);
      notify("Transaction record deleted.", "success");
      await load();
    } catch (requestError) {
      notify(requestError.message, "error");
    }
  };
  const exportRows = () => {
    try {
      downloadCsv(
        `${resource}.csv`,
        result.items,
        config.columns.map((column) => ({ label: column.label, value: (row) => row[column.key] })),
      );
    } catch (exportError) {
      notify(exportError.message, "error");
    }
  };

  return (
    <>
      <div className="page-heading-row">
        <div><span className="eyebrow">TRANSACTIONS</span><h2>{config.label}</h2><p>Browse live records from the order-to-cash system. Open any row to inspect related details.</p></div>
        {writesEnabled && <button className="button button-primary" onClick={() => setEditor({ open: true, record: null })}><Plus size={16} />New record</button>}
        <div className="records-count"><strong>{result.pagination?.total?.toLocaleString() ?? "—"}</strong><span>{config.label.toLowerCase()}</span></div>
      </div>
      <div className="filter-bar">
        <label className="search-field filter-search"><Search size={16} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Search records" /></label>
        <label className="status-filter"><span>Status</span><input value={filters.status} onChange={(event) => updateFilter("status", event.target.value.toUpperCase())} placeholder="All statuses" /></label>
        <label className="date-filter"><CalendarDays size={15} /><span>From</span><input aria-label="Date from" type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} /></label>
        <label className="date-filter"><span>To</span><input aria-label="Date to" type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} /></label>
        <button className="button button-quiet button-small" onClick={() => { setFilters({ search: "", status: "", date_from: "", date_to: "" }); setPage(1); }}><RotateCcw size={14} />Clear</button>
      </div>
      {error && !result.items.length ? <ErrorState message={error} onRetry={load} /> : (
        <DataTable
          columns={config.columns}
          rows={result.items}
          loading={loading}
          pagination={result.pagination}
          onPageChange={setPage}
          onView={viewRecord}
          onEdit={writesEnabled && resource !== "events" ? editRecord : undefined}
          onDelete={writesEnabled && resource !== "events" ? removeRecord : undefined}
          onExport={exportRows}
        />
      )}
      <DetailDrawer open={detail?.open} title={detail?.title || config.label} data={detail?.data} loading={detailLoading} error={detailError} onClose={() => setDetail(null)} />
      <RecordEditor open={editor.open} resource={resource} record={editor.record} onClose={() => setEditor({ open: false, record: null })} onSubmit={saveRecord} />
    </>
  );
}

export default function Transactions() {
  const { resource = "quotes" } = useParams();
  const [writesEnabled, setWritesEnabled] = useState(false);
  useEffect(() => {
    let active = true;
    capabilityApi.get().then((data) => {
      if (active) setWritesEnabled(Boolean(data.transaction_writes_enabled));
    }).catch(() => {
      if (active) setWritesEnabled(false);
    });
    return () => { active = false; };
  }, []);
  if (!resourceKeys.includes(resource)) return <Navigate to="/transactions/quotes" replace />;
  const config = TRANSACTION_RESOURCES[resource];

  return (
    <div className="page-stack">
      <div className="tabs-card">
        {resourceKeys.map((key) => (
          <NavLink key={key} to={`/transactions/${key}`} className={({ isActive }) => `transaction-tab ${isActive ? "active" : ""}`}>
            {TRANSACTION_RESOURCES[key].label}
          </NavLink>
        ))}
      </div>
      <ResourceTable resource={resource} config={config} writesEnabled={writesEnabled} />
    </div>
  );
}
