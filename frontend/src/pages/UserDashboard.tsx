import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Share, MessageSquare } from "lucide-react";
import DashboardCard from "../components/DashboardCard";
import Navbar from "../components/Navbar";
import RecommendationCarousel from "../components/RecommendationCarousel";
import { api } from "../services/auth";

interface Recommendation {
  id: string;
  title: string;
  filename?: string;
  fileLink?: string;
  original_filename?: string;
  author_name?: string;
  field?: string;
  keywords?: string[];
  meme_type?: string;
  created_at?: string;
}

export default function UserDashboard() {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // Fetch recommendations on component mount
  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const response = await api.get("/recommendations");
        const data = response.data;
        if (data.recommendations) {
          setRecommendations(data.recommendations);
        }
      } catch (error) {
        console.error("Failed to fetch recommendations:", error);
      }
    };

    fetchRecommendations();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            Knowledge Hub
          </h1>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <DashboardCard
              title="Search Knowledge"
              description="Explore our vast knowledge base to find answers to your questions"
              icon={Search}
              onClick={() => navigate("/user/search")}
            />
            <DashboardCard
              title="Share Knowledge"
              description="Contribute to the community by sharing your expertise"
              icon={Share}
              onClick={() => navigate("/user/share")}
            />
            <DashboardCard
              title="Chat with AI"
              description="Get instant answers and guidance from our AI assistant"
              icon={MessageSquare}
              onClick={() => navigate("/user/chat")}
            />
          </div>
          {/* NEW: Recommendation Section */}
          {recommendations.length > 0 && (
            <RecommendationCarousel recommendations={recommendations} />
          )}
        </div>
      </div>
    </div>
  );
}
