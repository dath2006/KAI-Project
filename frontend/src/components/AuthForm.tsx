import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserPlus, LogIn } from 'lucide-react';
import { login, signup } from '../services/auth';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

interface AuthFormProps {
  type: 'login' | 'signup';
  role: 'admin' | 'user';
}

export default function AuthForm({ type, role }: AuthFormProps) {
  const navigate = useNavigate();
  const { login: setAuth } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    field: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      let response;
      if (type === 'login') {
        response = await login(formData.email, formData.password, role);
      } else {
        response = await signup(
          formData.email,
          formData.password,
          formData.name,
          role,
          formData.field
        );
      }

      setAuth(response.token, response.user);
      toast.success(`Successfully ${type === 'login' ? 'logged in' : 'signed up'}!`);
      
      if (role === 'admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/user/dashboard');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold text-center mb-6">
        {type === 'login' ? 'Login' : 'Sign Up'} as {role}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {type === 'signup' && (
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          />
        </div>
        {type === 'signup' && role === 'user' && (
          <div>
            <label className="block text-sm font-medium text-gray-700">Learning Field</label>
            <select
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={formData.field}
              onChange={(e) => setFormData({ ...formData, field: e.target.value })}
            >
              <option value="">Select a field</option>
              <option value="computer-science">Computer Science</option>
              <option value="data-science">Data Science</option>
              <option value="artificial-intelligence">Artificial Intelligence</option>
              <option value="web-development">Web Development</option>
              <option value="mobile-development">Mobile Development</option>
              <option value="cybersecurity">Cybersecurity</option>
            </select>
          </div>
        )}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex items-center justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span>Loading...</span>
          ) : type === 'login' ? (
            <>
              <LogIn className="w-5 h-5 mr-2" />
              Login
            </>
          ) : (
            <>
              <UserPlus className="w-5 h-5 mr-2" />
              Sign Up
            </>
          )}
        </button>
      </form>
    </div>
  );
}