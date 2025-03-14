import React from 'react';
import './ResultsPanel.css';

function ResultsPanel({ results }) {
  if (!results || results.length === 0) {
    return (
      <div className="results-panel">
        <p>No results found. Please try a different search query.</p>
      </div>
    );
  }

  return (
    <div className="results-panel">
      {results.map((result) => (
        <div key={result.id} className="result-item">
          <h2>{result.title}</h2>
          <p>{result.content}</p>
          {result.tips && result.tips.length > 0 && (
            <div className="tips">
              <h3>Expert Tips:</h3>
              <ul>
                {result.tips.map((tip, idx) => (
                  <li key={idx}>
                    <strong>{tip.expert}:</strong> {tip.content}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="score">Relevance Score: {result.score.toFixed(2)}</p>
        </div>
      ))}
    </div>
  );
}

export default ResultsPanel;
