import React from 'react';
import '../styles/components/TopBar.css';

const TopBar = ({ title, onAddUrl, buttonText = 'Add URL' }) => {
  if (!onAddUrl) return (
    <div className="top-bar">
      <h1 className="page-title">{title}</h1>
    </div>
  );

  return (
    <div className="top-bar">
      <h1 className="page-title">{title}</h1>
      <button className="add-url-btn" onClick={onAddUrl}>
        <span>+</span>
        <span>{buttonText}</span>
      </button>
    </div>
  );
};

export default TopBar;