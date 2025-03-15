import React, { useState } from "react";
import { Search, ExternalLink } from "lucide-react";

interface SearchResult {
  id: string;
  title: string;
  fileLink?: string;
  keywords: string[];
  matched_keywords: string[];
  field: string;
  meme_type: string;
  filename: string;
  original_filename: string;
  score: number;
  author: string;
  created_at: string;
}

interface GroupedResults {
  [key: string]: SearchResult[];
}

interface Gap {
  id: string;
  topic: string;
}

export default function SearchKnowledge() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GroupedResults>({});
  const [selectedTitle, setSelectedTitle] = useState<string | null>(null);
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
      console.log(data);
      if (response.ok) {
        setSearchResults(data.results);
        setHasGaps(data.has_gaps);
        setGaps(data.gaps);
        // Select the first title by default if results exist
        const titles = Object.keys(data.results);
        setSelectedTitle(titles.length > 0 ? titles[0] : null);
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

        {/* Search Results Titles */}
        {isLoading ? (
          <p className="text-gray-500 text-center mt-6">Loading...</p>
        ) : Object.keys(searchResults).length > 0 && searchQuery.length > 0 ? (
          <div className="mt-6 space-y-4">
            {Object.entries(searchResults).map(([title, documents]) => (
              <div
                key={title}
                className={`p-4 border border-gray-200 rounded-lg cursor-pointer ${
                  selectedTitle === title
                    ? "border-blue-500 bg-blue-50"
                    : "hover:border-blue-500"
                }`}
                onClick={() => setSelectedTitle(title)}
              >
                <h3 className="font-semibold text-lg">{title}</h3>
                <p className="text-sm text-gray-600 mt-1">
                  {documents.length} document{documents.length !== 1 ? "s" : ""}
                </p>
              </div>
            ))}
          </div>
        ) : hasSearched ? (
          <p className="text-gray-500 text-center mt-6">
            No results found for "{searchQuery}"
          </p>
        ) : (
          <p className="text-gray-500 text-center mt-6">
            Please enter a search query
          </p>
        )}
      </div>

      {/* Content Area (70%) */}
      <div className="flex-1 p-6 overflow-auto">
        {selectedTitle && searchResults[selectedTitle] ? (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold mb-6">{selectedTitle}</h2>
            {searchResults[selectedTitle].map((doc) => (
              <div
                key={doc.id}
                className="bg-white rounded-lg shadow-sm p-6 space-y-4"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold">{doc.filename}</h3>
                    <p className="text-sm text-gray-600">
                      Type: {doc.meme_type}
                    </p>
                    <p className="text-sm text-gray-600">
                      Original File:{" "}
                      <span
                        className={`${
                          doc.original_filename
                            .toLowerCase()
                            .includes(searchQuery.toLowerCase())
                            ? "bg-yellow-100 px-1 rounded"
                            : ""
                        }`}
                      >
                        {doc.original_filename}
                      </span>
                    </p>
                  </div>
                  {doc.fileLink && (
                    <a
                      href={doc.fileLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-blue-600 hover:text-blue-800"
                    >
                      Open File <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">
                    Matched Keywords:
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {doc.matched_keywords.map((keyword, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  <p>Author: {doc.author}</p>
                  <p>
                    Created: {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                  <p>Field: {doc.field}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <p className="text-gray-500 text-center">
              Select a title from the left to view documents
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
