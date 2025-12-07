import React, { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';
import HealthTimeline from './HealthTimeline';
import api from '../services/api';
import '../styles/components/Table.css';

const URLTable = ({ urls, healthStatuses, onEdit, onDelete, onRefresh, servers = [] }) => {
  const [toggleStates, setToggleStates] = useState({});

  // Initialize toggle states from URLs (health_check_status: 'YES'/'NO')
  useEffect(() => {
    const states = {};
    urls.forEach(url => {
      states[url.id] = url.health_check_status === 'YES';
    });
    setToggleStates(states);
  }, [urls]);
  
  // Get server info by server_idcd
  const getServerInfo = (serverId) => {
    return servers.find(s => s.id === serverId) || null;
  };
  const getHealthStatus = (urlId) => {
    const health = healthStatuses.find(h => h.url_id === urlId);
    return health?.status || 'offline';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleToggleHealthCheck = async (urlId, currentStatus) => {
    // Optimistic update - update UI immediately for smooth UX
    setToggleStates(prev => ({
      ...prev,
      [urlId]: !currentStatus
    }));
    
    try {
      const newStatus = !currentStatus ? 'YES' : 'NO';
      await api.patch(`/api/urls/${urlId}/health-check`, { status: newStatus });
      
      console.log('Toggle successful');
      // Refresh to get updated data from server
      if (onRefresh) {
        await onRefresh();
      }
    } catch (error) {
      // Revert on error
      console.error('Error toggling health check:', error);
      setToggleStates(prev => ({
        ...prev,
        [urlId]: currentStatus
      }));
      alert('Failed to toggle health check');
    }
  };

  if (urls.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon"></div>
        <div className="empty-title">No URLs Found</div>
        <div className="empty-text">Add your first URL to start monitoring</div>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Project Name</th>
            <th>URL</th>
            <th>Server Name</th>
            <th>Last Check Time</th>
            <th>Status</th>
            <th>Last 10 Minutes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {urls.map((url) => {
            const serverInfo = getServerInfo(url.server_id);
            const isHealthCheckEnabled = toggleStates[url.id];
            return (
              <tr key={url.id}>
                <td>{url.project_name}</td>
                <td>
                  <a href={url.url} target="_blank" rel="noopener noreferrer">
                    {url.url}
                  </a>
                </td>
                <td>{serverInfo?.server_name || 'N/A'}</td>
                <td>{formatDate(url.updated_at)}</td>
                <td>
                  {isHealthCheckEnabled ? (
                    <StatusBadge status={getHealthStatus(url.id)} />
                  ) : (
                    <span style={{ color: '#94a3b8', fontSize: '13px' }}>Disabled</span>
                  )}
                </td>
                <td>
                  {isHealthCheckEnabled ? (
                    <HealthTimeline urlId={url.id} />
                  ) : (
                    <span style={{ color: '#94a3b8', fontSize: '13px' }}>N/A</span>
                  )}
                </td>
              <td>
                <div className="action-buttons">
                  {onEdit && (
                    <button className="action-btn edit" onClick={() => onEdit(url)}>
                      Edit
                    </button>
                  )}
                  {onDelete && (
                    <button className="action-btn delete" onClick={() => onDelete(url.id)}>
                      Delete
                    </button>
                  )}
                  {onEdit && (
                    <label className="health-check-toggle" title={`Health Check: ${toggleStates[url.id] ? 'ON' : 'OFF'}`}>
                      <input
                        type="checkbox"
                        checked={toggleStates[url.id] || false}
                        onChange={() => handleToggleHealthCheck(url.id, toggleStates[url.id])}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                  )}
                  {url.description && (
                    <button
                      className="action-btn description-btn"
                      title={url.description}
                    >
                      i
                    </button>
                  )}
                  {!onEdit && !onDelete && (
                    <span style={{ color: '#94a3b8', fontSize: '13px' }}>Read Only</span>
                  )}
                </div>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default URLTable;