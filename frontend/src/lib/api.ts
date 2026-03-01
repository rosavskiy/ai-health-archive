import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Автоматически добавляем JWT токен
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 → редирект на логин
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// ── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (email: string, password: string) =>
    api.post("/api/auth/register", { email, password, consent_accepted: true }),
  login: (email: string, password: string) =>
    api.post("/api/auth/login", new URLSearchParams({ username: email, password }), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  verifyTotp: (temp_token: string, code: string) =>
    api.post("/api/auth/totp/verify-full", { temp_token, code }),
  setupTotp: () => api.post("/api/auth/totp/setup"),
  enableTotp: (code: string) => api.post("/api/auth/totp/enable", { code }),
};

// ── Documents ───────────────────────────────────────────────────────────────
export const docsApi = {
  list: (search?: string) => api.get("/api/documents/", { params: { search } }),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  download: (docId: string) => api.get(`/api/documents/${docId}/download`, { responseType: "blob" }),
  delete: (docId: string) => api.delete(`/api/documents/${docId}`),
};

// ── Metrics ─────────────────────────────────────────────────────────────────
export const metricsApi = {
  summary: () => api.get("/api/metrics/summary"),
  names: () => api.get("/api/metrics/names"),
  trend: (name: string) => api.get(`/api/metrics/trend/${encodeURIComponent(name)}`),
};

// ── AI Chat ─────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (messages: { role: string; content: string }[]) =>
    api.post("/api/chat/", { messages }),
};

// ── Notifications ───────────────────────────────────────────────────────────
export const notifApi = {
  list: () => api.get("/api/notifications/"),
  subscribe: (subscription: PushSubscriptionJSON) =>
    api.post("/api/notifications/subscribe", {
      endpoint: subscription.endpoint,
      keys: subscription.keys,
    }),
};
