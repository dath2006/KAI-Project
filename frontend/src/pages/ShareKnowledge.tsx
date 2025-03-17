import React, { useState } from "react";
import { MessageSquare, Video, Upload } from "lucide-react";
import { api } from "../services/auth";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import { useNavigate } from "react-router-dom";

export default function ShareKnowledge() {
  const { user } = useAuth();
  const [topic, setTopic] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowOptions(true);
  };

  const handleFileUpload = async () => {
    if (!file) {
      toast.error("Please select a file first");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("topic", topic);

    try {
      await api.post("/knowledge/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      toast.success("File uploaded successfully!");
      setFile(null);
      setTopic("");
      setShowOptions(false);
    } catch (error) {
      toast.error("Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-sm p-8">
            <h1 className="text-2xl font-bold mb-6">Share Your Knowledge</h1>

            {!showOptions ? (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="topic"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    What would you like to share knowledge about?
                  </label>
                  <input
                    type="text"
                    id="topic"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your topic..."
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Continue
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                <h2 className="text-xl font-semibold mb-4">
                  How would you like to share?
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    className="p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors flex flex-col items-center"
                    onClick={() => {
                      /* TODO: Implement meeting logic */
                    }}
                  >
                    <Video className="h-12 w-12 text-blue-600 mb-2" />
                    <span className="font-medium">Through Meeting</span>
                    <p className="text-sm text-gray-500 mt-2 text-center">
                      Schedule a live session to share your knowledge
                    </p>
                  </button>

                  <button
                    className="p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors flex flex-col items-center"
                    onClick={() => {
                      /* TODO: Implement chat logic */
                      navigate("/user/ai-chat");
                    }}
                  >
                    <MessageSquare className="h-12 w-12 text-blue-600 mb-2" />
                    <span className="font-medium">Through Chat</span>
                    <p className="text-sm text-gray-500 mt-2 text-center">
                      Share your knowledge via chat messaging
                    </p>
                  </button>

                  <button
                    className="p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors flex flex-col items-center"
                    onClick={() => {
                      /* TODO: Implement chat logic */
                      navigate("/user/upload");
                    }}
                  >
                    <Upload className="h-12 w-12 text-blue-600 mb-2" />
                    <span className="font-medium">Upload File</span>
                    <p className="text-sm text-gray-500 mt-2 text-center mb-4">
                      Share your knowledge through a document
                    </p>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
