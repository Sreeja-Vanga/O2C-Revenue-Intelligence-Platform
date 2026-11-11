import axios from "axios";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api"
).replace(/\/+$/, "");

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { Accept: "application/json" },
});

client.interceptors.response.use(
  (response) => {
    if (response.config.responseType === "blob") return response;
    const body = response.data;
    if (!body?.success) {
      return Promise.reject(new Error(body?.message || "The API request failed."));
    }
    return body.data;
  },
  (error) => {
    const message =
      error.response?.data?.message ||
      error.message ||
      "The server could not be reached. Check the API connection and try again.";
    return Promise.reject(new Error(message));
  },
);

function queryString(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  });
  const result = search.toString();
  return result ? `?${result}` : "";
}

export const api = {
  get: (path, params) => client.get(`${path}${queryString(params)}`),
  post: (path, body) => client.post(path, body),
  put: (path, body) => client.put(path, body),
};

export const dashboardApi = {
  overview: () => api.get("/dashboard/overview"),
  revenue: () => api.get("/dashboard/revenue-summary"),
  anomalySummary: () => api.get("/dashboard/anomaly-summary"),
  lifecycle: () => api.get("/dashboard/lifecycle-summary"),
};

export const analyticsApi = {
  revenueLeakage: () => api.get("/analytics/revenue-leakage"),
  orderPerformance: () => api.get("/analytics/order-performance"),
  invoicePerformance: () => api.get("/analytics/invoice-performance"),
  paymentPerformance: () => api.get("/analytics/payment-performance"),
  trends: () => api.get("/analytics/trends"),
  invoiceAging: () => api.get("/analytics/invoice-aging"),
  outstandingReceivables: () => api.get("/analytics/outstanding-receivables"),
  disputeAnalysis: () => api.get("/analytics/dispute-analysis"),
  lifecyclePerformance: () => api.get("/analytics/lifecycle-performance"),
  reconciliation: () => api.get("/analytics/reconciliation"),
  reconciliationDetails: () => api.get("/analytics/reconciliation/details"),
};

export const exceptionApi = {
  list: (params) => api.get("/exceptions", params),
  get: (id) => api.get(`/exceptions/${encodeURIComponent(id)}`),
  source: (id) => api.get(`/exceptions/${encodeURIComponent(id)}/source`),
  summary: () => api.get("/exceptions/summary"),
  updateStatus: (id, status) =>
    api.put(`/exceptions/${encodeURIComponent(id)}/status`, { status }),
};

export const detectionApi = {
  run: () => api.post("/detection/run"),
  results: () => api.get("/detection/results"),
  summary: () => api.get("/detection/summary"),
};

export const transactionApi = {
  list: (resource, params) => api.get(`/${resource}`, params),
  get: (resource, id) => api.get(`/${resource}/${encodeURIComponent(id)}`),
  schema: (resource) => api.get(`/resource-schema/${resource}`),
  create: (resource, body) => api.post(`/${resource}`, body),
  update: (resource, id, body) => api.put(`/${resource}/${encodeURIComponent(id)}`, body),
  delete: (resource, id) => client.delete(`/${resource}/${encodeURIComponent(id)}`),
};

export const capabilityApi = {
  get: () => api.get("/capabilities"),
};

export const healthApi = {
  get: () => api.get("/health"),
};

export const syntheticDataApi = {
  start: (profile) => api.post("/synthetic-data/jobs", { profile }),
  getJob: (jobId) => api.get(`/synthetic-data/jobs/${encodeURIComponent(jobId)}`),
};

export async function downloadFinancialReport() {
  try {
    const response = await client.get("/reports/financial.xlsx", {
      responseType: "blob",
    });
    if (!response.headers["content-type"]?.includes("spreadsheetml")) {
      const body = await response.data.text();
      let message = "The server did not return an Excel workbook.";
      try {
        message = JSON.parse(body).message || message;
      } catch {
        message = body || message;
      }
      throw new Error(message);
    }
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "o2c-financial-report.xlsx";
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    const message = error.response?.data instanceof Blob
      ? await error.response.data.text()
      : "";
    throw new Error(message || error.message || "The Excel report could not be downloaded.");
  }
}

export function downloadCsv(filename, rows, columns) {
  if (!rows?.length) {
    throw new Error("There are no loaded rows to export.");
  }
  const escapeCell = (value) => {
    const text = value == null ? "" : String(value);
    return `"${text.replaceAll('"', '""')}"`;
  };
  const headings = columns.map((column) => column.label);
  const lines = [
    headings.map(escapeCell).join(","),
    ...rows.map((row) =>
      columns.map((column) => escapeCell(column.value(row))).join(","),
    ),
  ];
  const blob = new Blob([`\uFEFF${lines.join("\r\n")}`], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
