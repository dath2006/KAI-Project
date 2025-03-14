import React, { useState } from "react";
import { Search } from "lucide-react";

interface SearchResult {
  id: string;
  content: string;
  score: number;
  type: string;
  title: string;
  tips: string[];
  source: string[];
}

interface Gap {
  id: string;
  topic: string;
}

export default function SearchKnowledge() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [hasGaps, setHasGaps] = useState(false);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoading(true);
      const response = await fetch("http://localhost:8080/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: searchQuery }),
      });
      const data = await response.json();
      if (response.ok) {
        setSearchResults(data.results);
        setHasGaps(data.has_gaps);
        setGaps(data.gaps);
      } else {
        console.error("Search error: ", data.error);
      }
      setIsLoading(false);
    } catch (error) {
      console.error("Error during search: ", error);
      setIsLoading(false);
    }
    setHasSearched(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Search Panel (30%) */}
      <div className="w-[30%] bg-white border-r border-gray-200 p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search knowledge..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Search
          </button>
        </form>

        {/* Search Results */}
        {isLoading ? (
          <p className="text-gray-500 text-center">Loading...</p>
        ) : searchResults.length > 0 && searchQuery.length > 0 ? (
          <div className="mt-6 space-y-4">
            {searchResults.map((result) => (
              <div
                key={result.id}
                className="p-4 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer"
              >
                <h3 className="font-semibold text-lg">{result.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{result.content}</p>
              </div>
            ))}
          </div>
        ) : hasSearched && searchResults.length === 0 ? (
          <p className="text-gray-500 text-center">
            No results found for "{searchQuery}"
          </p>
        ) : (
          <p className="text-gray-500 text-center">
            Please enter a search query
          </p>
        )}
      </div>

      {/* Content Area (70%) */}
      <div className="flex-1 p-6">
        {hasGaps ? (
          <div className="bg-white rounded-lg shadow-sm p-6 min-h-[calc(100vh-3rem)]">
            <p className="text-gray-500 text-center">
              {gaps.map((gap, index) => (
                <p key={index}>{gap.topic}</p>
              ))}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm p-6 min-h-[calc(100vh-3rem)]">
            <p className="text-gray-500 text-center">
              Select a knowledge item to view its content
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
