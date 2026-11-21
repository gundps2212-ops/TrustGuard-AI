import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api" });
api.interceptors.request.use((config) => {
  const session = localStorage.getItem("tg_session");
  if (session) {
    const parsed = JSON.parse(session);
    config.headers.Authorization = `Bearer ${parsed.access_token}`;
    config.headers["X-Refresh-Token"] = parsed.refresh_token;
  }
  return config;
});
export default api;