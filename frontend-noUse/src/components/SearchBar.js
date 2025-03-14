import React, { useState } from 'react';
import './SearchBar.css';

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('');

  const handleInputChange = (e) => {
    setQuery(e.target.value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Search for documents or expert tips..."
        value={query}
        onChange={handleInputChange}
        list="autocompleteOptions"
      />
      <datalist id="autocompleteOptions">
        {/* Static autocomplete suggestions – you can later make these dynamic */}
        <option value="Machine Learning" />
        <option value="Data Science" />
        <option value="AI" />
        <option value="Knowledge Management" />
      </datalist>
      <button type="submit">Search</button>
    </form>
  );
}

export default SearchBar;
