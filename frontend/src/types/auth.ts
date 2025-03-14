export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  field?: string; // Learning field for users
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}