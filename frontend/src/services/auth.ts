import { User } from "../types/auth";

interface LoginResponse {
  token: string;
  user: User;
}

export async function login(
  email: string,
  password: string,
  role: "admin" | "user",
  field?: string
): Promise<LoginResponse> {
  const response = await fetch("http://localhost:8080/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, role, field }),
  });

  if (!response.ok) {
    const error = await response.json();
    console.log("error");
    throw new Error(error.message || "Failed to login");
  }

  const data = await response.json();
  return data;
}

export async function signup(
  email: string,
  password: string,
  name: string,
  role: "admin" | "user",
  field?: string
): Promise<LoginResponse> {
  const response = await fetch("http://localhost:8080/api/auth/signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, name, role, field }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "Failed to sign up");
  }

  const data = await response.json();
  return data;
}
