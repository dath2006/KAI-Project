import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Share, MessageSquare } from 'lucide-react';
import DashboardCard from '../components/DashboardCard';

export default function UserDashboard() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Knowledge Hub</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <DashboardCard
            title="Search Knowledge"
            description="Explore our vast knowledge base to find answers to your questions"
            icon={Search}
            onClick={() => navigate('/user/search')}
          />
          <DashboardCard
            title="Share Knowledge"
            description="Contribute to the community by sharing your expertise"
            icon={Share}
            onClick={() => navigate('/user/share')}
          />
          <DashboardCard
            title="Chat with AI"
            description="Get instant answers and guidance from our AI assistant"
            icon={MessageSquare}
            onClick={() => navigate('/user/chat')}
          />
        </div>
      </div>
    </div>
  );
}