import React from "react";
import { useNavigate } from "react-router-dom";
import { Eye, Upload, AlertTriangle } from "lucide-react";
import DashboardCard from "../components/DashboardCard";
import Navbar from "../components/Navbar";

export default function AdminDashboard() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            Admin Dashboard
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
              onClick={() => navigate("/admin/upload")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
