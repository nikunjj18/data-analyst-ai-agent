import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

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

export const getChartUrl = () => {
  return `${API_BASE_URL}/chart?t=${Date.now()}`; // cache-bust so new charts always load
};