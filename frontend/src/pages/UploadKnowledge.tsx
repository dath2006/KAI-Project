import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Upload } from "lucide-react";
import Navbar from "../components/Navbar";
import { api } from "../services/auth";
import toast from "react-hot-toast";

export default function UploadKnowledge() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = location.pathname.includes("/admin");

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
      const endpoint = isAdmin
        ? "/admin/knowledge/upload"
        : "/user/knowledge/upload";
      await api.post(endpoint, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      toast.success("Knowledge content uploaded successfully!");
      setFile(null);
      setTopic("");
      navigate(isAdmin ? "/admin/dashboard" : "/user/dashboard");
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
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">
              Upload Knowledge
            </h1>
            <button
              onClick={() =>
                navigate(isAdmin ? "/admin/dashboard" : "/user/dashboard")
              }
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back to Dashboard
            </button>
          </div>

          <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="p-8">
              <div className="flex items-center justify-center mb-8">
                <div className="bg-blue-50 rounded-full p-4">
                  <Upload className="h-8 w-8 text-blue-600" />
                </div>
              </div>

              <div className="space-y-6">
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
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
                    <input
                      type="file"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                      className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    <p className="mt-2 text-sm text-gray-500">
                      Drag and drop your file here, or click to select
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-100 px-8 py-4 bg-gray-50">
              <div className="flex justify-end space-x-4">
                <button
                  onClick={() =>
                    navigate(isAdmin ? "/admin/dashboard" : "/user/dashboard")
                  }
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFileUpload}
                  disabled={!file || !topic || uploading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-all duration-200 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Upload className="h-5 w-5" />
                  {uploading ? "Uploading..." : "Upload Content"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
