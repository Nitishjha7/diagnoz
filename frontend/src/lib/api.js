// In dev (vite dev server) default to the local backend directly. In the Docker/Nginx
// build, VITE_API_BASE_URL is left unset so requests go out as relative paths and Nginx's
// /api/ and /ws/ proxy_pass rules (see nginx.conf) route them to the backend container.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");
const WS_BASE = API_BASE
  ? API_BASE.replace(/^http/, "ws")
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

function authHeaders() {
  const token = localStorage.getItem("diagnoz_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  base: API_BASE,
  wsBase: WS_BASE,

  register(payload) {
    return request("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  async login(email, password) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const data = await request("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    localStorage.setItem("diagnoz_token", data.access_token);
    return data;
  },

  logout() {
    localStorage.removeItem("diagnoz_token");
  },

  me() {
    return request("/api/v1/auth/me");
  },

  isAuthenticated() {
    return Boolean(localStorage.getItem("diagnoz_token"));
  },

  createSession() {
    return request("/api/v1/sessions", { method: "POST" });
  },

  getSession(sessionId) {
    return request(`/api/v1/sessions/${sessionId}`);
  },

  createTechnicianProfile(latitude, longitude) {
    return request("/api/v1/technicians/me/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude, longitude }),
    });
  },

  setTechnicianAvailability(isAvailable) {
    return request(`/api/v1/technicians/me/availability?is_available=${isAvailable}`, {
      method: "PATCH",
    });
  },

  createDispatch(latitude, longitude, sessionId) {
    return request("/api/v1/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude, longitude, session_id: sessionId || null }),
    });
  },

  getDispatch(dispatchId) {
    return request(`/api/v1/dispatch/${dispatchId}`);
  },

  acceptDispatch(dispatchId) {
    return request(`/api/v1/dispatch/${dispatchId}/accept`, { method: "POST" });
  },

  verifyStartOtp(dispatchId, otp) {
    return request(`/api/v1/dispatch/${dispatchId}/verify-start-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ otp }),
    });
  },

  verifyEndOtp(dispatchId, otp) {
    return request(`/api/v1/dispatch/${dispatchId}/verify-end-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ otp }),
    });
  },
};
