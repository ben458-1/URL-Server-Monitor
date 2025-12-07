import React from 'react';
import '../styles/components/StatusBadge.css';

const StatusBadge = ({ status }) => {
  return (
    <span className={`status-badge ${status}`}>
      <span className={`status-dot ${status}`}></span>
      {status.toUpperCase()}
    </span>
  );
};

export default StatusBadge;