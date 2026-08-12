import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

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

export const getChartUrl = () => `${API_BASE_URL}/chart?t=${Date.now()}`;

export const getDatasetSummary = async () => {
  const response = await api.get("/dataset-summary");
  return response.data;
};

export const getTableDashboard = async (tableName) => {
  const response = await api.get("/table-dashboard", { params: { table_name: tableName } });
  return response.data;
};

export const getInsights = async () => {
  const response = await api.get("/generate-insights");
  return response.data;
};

export const exportReportUrl = () => `${API_BASE_URL}/export-report`;