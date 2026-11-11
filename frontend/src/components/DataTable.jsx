import React from "react";
import { ChevronLeft, ChevronRight, Download, Eye, Pencil, Search, Trash2 } from "lucide-react";
import { EmptyState, LoadingState } from "./PageState";

export default function DataTable({
  columns,
  rows = [],
  loading = false,
  search,
  onSearch,
  searchPlaceholder = "Search records",
  pagination,
  onPageChange,
  onView,
  onEdit,
  onDelete,
  onExport,
  toolbar,
  emptyTitle,
}) {
  return (
    <div className="table-card">
      {(onSearch || toolbar || onExport) && (
        <div className="table-toolbar">
          {onSearch && (
            <label className="search-field">
              <Search size={16} />
              <input value={search || ""} onChange={(event) => onSearch(event.target.value)} placeholder={searchPlaceholder} />
            </label>
          )}
          {toolbar}
          <div className="toolbar-spacer" />
          {onExport && (
            <button className="button button-secondary button-small" onClick={onExport} disabled={!rows.length}>
              <Download size={15} />Export CSV
            </button>
          )}
        </div>
      )}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr>{columns.map((column) => <th key={column.key} className={column.numeric ? "align-right" : ""}>{column.label}</th>)}{(onView || onEdit || onDelete) && <th className="action-heading">Action</th>}</tr></thead>
          {!loading && rows.length > 0 && (
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={row.id ?? row.exception_id ?? row.account_id ?? row.invoice_id ?? row.payment_id ?? row.quote_id ?? row.sales_order_id ?? row.shipment_id ?? row.dispute_id ?? row.status_event_id ?? rowIndex}>
                  {columns.map((column) => (
                    <td key={column.key} className={column.numeric ? "align-right" : ""}>
                      {column.render ? column.render(row) : (row[column.key] ?? "—")}
                    </td>
                  ))}
                  {(onView || onEdit || onDelete) && <td className="action-cell">
                    {onView && <button className="button-icon" onClick={() => onView(row)} aria-label="View record"><Eye size={16} /><span>View</span></button>}
                    {onEdit && <button className="button-icon" onClick={() => onEdit(row)} aria-label="Edit record"><Pencil size={15} /><span>Edit</span></button>}
                    {onDelete && <button className="button-icon danger-action" onClick={() => onDelete(row)} aria-label="Delete record"><Trash2 size={15} /><span>Delete</span></button>}
                  </td>}
                </tr>
              ))}
            </tbody>
          )}
        </table>
        {loading && <LoadingState label="Loading records…" />}
        {!loading && !rows.length && <EmptyState title={emptyTitle || "No records found"} />}
      </div>
      {pagination && pagination.pages > 1 && (
        <div className="table-pagination">
          <span>Showing page <strong>{pagination.page}</strong> of <strong>{pagination.pages}</strong><span className="pagination-total"> · {pagination.total.toLocaleString()} records</span></span>
          <div className="pagination-actions">
            <button className="icon-button" disabled={pagination.page <= 1} onClick={() => onPageChange(pagination.page - 1)} aria-label="Previous page"><ChevronLeft size={17} /></button>
            <button className="icon-button" disabled={pagination.page >= pagination.pages} onClick={() => onPageChange(pagination.page + 1)} aria-label="Next page"><ChevronRight size={17} /></button>
          </div>
        </div>
      )}
    </div>
  );
}