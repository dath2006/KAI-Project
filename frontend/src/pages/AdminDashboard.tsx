import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, Upload } from "lucide-react";
import DashboardCard from "../components/DashboardCard";
import Navbar from "../components/Navbar";
import { api } from "../services/auth";
import toast from "react-hot-toast";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [topic, setTopic] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async () => {
    if (!file || !topic) {
      toast.error("Please provide both topic and file");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("topic", topic);

    try {
      await api.post("/admin/knowledge/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      toast.success("Knowledge content uploaded successfully!");
      setFile(null);
      setTopic("");
      setShowUploadForm(false);
    } catch (error) {
      toast.error("Failed to upload content");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            Admin Dashboard
          </h1>

          {!showUploadForm ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <DashboardCard
                title="View Knowledge Gaps"
                description="Analyze and identify areas where more content is needed"
                icon={Eye}
                onClick={() => navigate("/admin/gaps")}
              />
              <DashboardCard
                title="Add New Knowledge"
                description="Upload new educational content"
                icon={Upload}
                onClick={() => setShowUploadForm(true)}
              />
            </div>
          ) : (
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-sm">
              <h2 className="text-2xl font-semibold mb-6">
                Upload Knowledge Content
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Topic/Title
                  </label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter the topic or title..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Upload File
                  </label>
                  <input
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={handleFileUpload}
                    disabled={!file || !topic || uploading}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? "Uploading..." : "Upload Content"}
                  </button>
                  <button
                    onClick={() => setShowUploadForm(false)}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
