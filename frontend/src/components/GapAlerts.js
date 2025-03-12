import React from 'react';
import './GapAlerts.css';

function GapAlerts({ gaps }) {
  return (
    <div className="gap-alerts">
      <p>
        ⚠ {gaps.length} topic{gaps.length > 1 ? 's' : ''} lack expert advice!
      </p>
    </div>
  );
}

export default GapAlerts;
