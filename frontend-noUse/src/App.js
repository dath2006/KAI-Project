import React, { useState } from "react";
import SearchBar from "./components/SearchBar";
import ResultsPanel from "./components/ResultsPanel";
import GapAlerts from "./components/GapAlerts";
import "./App.css";

function App() {
  // State for search results and gap information
  const [results, setResults] = useState([]);
  const [hasGaps, setHasGaps] = useState(false);
  const [gaps, setGaps] = useState([]);

  // Function to call the backend search API
  const handleSearch = async (query) => {
    try {
      const response = await fetch("http://localhost:8080/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      if (response.ok) {
        setResults(data.results);
        setHasGaps(data.has_gaps);
        setGaps(data.gaps);
      } else {
        console.error("Search error: ", data.error);
      }
    } catch (error) {
      console.error("Error during search: ", error);
    }
  };

  return (
    <div className="app-container">
      <h1>Expert Search</h1>
      <SearchBar onSearch={handleSearch} />
      {hasGaps && <GapAlerts gaps={gaps} />}
      <ResultsPanel results={results} />
    </div>
  );
}

export default App;
