import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API,
  timeout: 60000,
  headers: { "Content-Type": "application/json;charset=utf-8" },
});

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      "请求失败";
    ElMessage.error(typeof message === "string" ? message : JSON.stringify(message));
    return Promise.reject(error);
  },
);

export default http;
