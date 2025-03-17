import React, { useState, useEffect } from "react";
import { Upload, RefreshCw, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { api } from "../services/auth";
import toast from "react-hot-toast";
import "./KnowledgeGaps.css";

interface KnowledgeGap {
  topic: string;
  reason: string;
}

interface GapsResponse {
  gaps: KnowledgeGap[];
  html_content: string;
}

export default function KnowledgeGaps() {
  const navigate = useNavigate();
  const [gapsData, setGapsData] = useState<GapsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTopic, setSearchTopic] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const fetchGaps = async () => {
    setLoading(true);
    try {
      const response = await api.get("/gaps");
      setGapsData(response.data);
    } catch (error) {
      toast.error("Failed to fetch knowledge gaps");
    } finally {
      setLoading(false);
    }
  };

  const analyzeSpecificTopic = async () => {
    if (!searchTopic.trim()) {
      toast.error("Please enter a topic to analyze");
      return;
    }

    setAnalyzing(true);
    try {
      const response = await api.post("/detect_gaps", { topic: searchTopic });
      setGapsData(response.data);
      toast.success("Gap analysis completed");
    } catch (error) {
      toast.error("Failed to analyze topic");
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    fetchGaps();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Knowledge Gaps</h1>
            <button
              onClick={() => navigate("/admin/dashboard")}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back to Dashboard
            </button>
          </div>

          {/* Search and Analysis Section */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
            <div className="flex gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  value={searchTopic}
                  onChange={(e) => setSearchTopic(e.target.value)}
                  placeholder="Enter a topic to analyze for gaps..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={analyzeSpecificTopic}
                disabled={analyzing}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Search className="h-5 w-5" />
                {analyzing ? "Analyzing..." : "Analyze Topic"}
              </button>
              <button
                onClick={fetchGaps}
                disabled={loading}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                <RefreshCw className="h-5 w-5" />
                Refresh
              </button>
            </div>
          </div>

          {/* Gaps Display */}
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading gaps...</p>
            </div>
          ) : gapsData ? (
            <div className="space-y-6">
              {/* HTML Content Display */}
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="p-8">
                  <div
                    className="prose prose-lg max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-p:text-gray-600 prose-p:leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: gapsData.html_content }}
                  />
                </div>
                <div className="border-t border-gray-100 px-8 py-4 bg-gray-50 flex justify-end">
                  <button
                    onClick={() => navigate("/admin/upload")}
                    className="add-content-button inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-all duration-200 ease-in-out"
                  >
                    <Upload className="h-5 w-5" />
                    Add Content
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg shadow-sm">
              <div className="text-gray-400 mb-3">
                <Search className="h-12 w-12 mx-auto" />
              </div>
              <p className="text-gray-600 text-lg">
                No knowledge gaps found. Try analyzing a specific topic.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
