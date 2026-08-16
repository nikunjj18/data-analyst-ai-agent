import axios from "axios";
export const exportDashboardUrl = () => `${API_BASE_URL}/export-dashboard`;

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const api = axios.create({ baseURL: API_BASE_URL });

export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const askQuestion = async (question) => {
  const response = await api.post("/ask", { question });
  return response.data;
};

export const getChartUrlById = (chartId) => `${API_BASE_URL}/chart/${chartId}`;

export const getTableDashboard = async (tableName) => {
  const response = await api.get("/table-dashboard", { params: { table_name: tableName } });
  return response.data;
};

export const getInsights = async () => {
  const response = await api.get("/generate-insights");
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get("/history");
  return response.data;
};

export const switchDataset = async (id) => {
  const response = await api.post("/switch-dataset", { id });
  return response.data;
};

export const exportReportUrl = () => `${API_BASE_URL}/export-report`;