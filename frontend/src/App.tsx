import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import AuthForm from "./components/AuthForm";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import SearchKnowledge from "./pages/SearchKnowledge";
import ShareKnowledge from "./pages/ShareKnowledge";
import ChatWithAI from "./pages/ChatWithAI";
import ChatQA from "./pages/ChatQA";
import KnowledgeGaps from "./pages/KnowledgeGaps";
import UploadKnowledge from "./pages/UploadKnowledge";

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-100">
          <Toaster position="top-right" />
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* Auth Routes */}
            <Route
              path="/login"
              element={
                <div className="min-h-screen flex items-center justify-center p-4">
                  <AuthForm type="login" role="user" />
                </div>
              }
            />
            <Route
              path="/admin/login"
              element={
                <div className="min-h-screen flex items-center justify-center p-4">
                  <AuthForm type="login" role="admin" />
                </div>
              }
            />
            <Route
              path="/signup"
              element={
                <div className="min-h-screen flex items-center justify-center p-4">
                  <AuthForm type="signup" role="user" />
                </div>
              }
            />

            {/* Dashboard Routes */}
            <Route path="/user/dashboard" element={<UserDashboard />} />
            <Route path="/admin/dashboard" element={<AdminDashboard />} />

            {/* User Feature Routes */}
            <Route path="/user/search" element={<SearchKnowledge />} />
            <Route path="/user/share" element={<ShareKnowledge />} />
            <Route path="/user/chat" element={<ChatWithAI />} />
            <Route path="/user/upload" element={<UploadKnowledge />} />
            {/* Chat QA Route */}
            <Route path="/user/ai-chat" element={<ChatQA />} />
            <Route path="/admin/gaps" element={<KnowledgeGaps />} />
            <Route path="/admin/upload" element={<UploadKnowledge />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
