import axios from "axios";
import { User } from "../types/auth";

const API_URL = "http://localhost:8080/api";

interface LoginResponse {
  token: string;
  user: User;
}

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add token to requests if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(
  email: string,
  password: string,
  role: "admin" | "user"
): Promise<LoginResponse> {
  try {
    const response = await api.post("/auth/login", { email, password, role });
    const { token, user } = response.data;

    // Store token in localStorage
    localStorage.setItem("token", token);

    // Set default authorization header for future requests
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;

    return { token, user };
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data.message || "Failed to login");
    }
    throw new Error("Failed to login");
  }
}

export async function signup(
  email: string,
  password: string,
  name: string,
  role: "admin" | "user",
  field?: string
): Promise<LoginResponse> {
  try {
    const response = await api.post("/auth/signup", {
      email,
      password,
      name,
      role,
      field,
    });
    const { token, user } = response.data;

    // Store token in localStorage
    localStorage.setItem("token", token);

    // Set default authorization header for future requests
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;

    return { token, user };
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data.message || "Failed to sign up");
    }
    throw new Error("Failed to sign up");
  }
}

// Export the configured axios instance for other API calls
export { api };
