import React from 'react';
import '../styles/components/Table.css';

const ServerTable = ({ servers, onEdit, onDelete }) => {
  if (!servers || servers.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🖥️</div>
        <div className="empty-title">No Servers Found</div>
        <div className="empty-text">Add your first server to get started</div>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Server Name</th>
            <th>Port</th>
            <th>Location</th>
            <th>Created At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {servers.map((server) => (
            <tr key={server.id}>
              <td>{server.server_name}</td>
              <td>{server.port || '-'}</td>
              <td>{server.server_location}</td>
              <td>
                {new Date(server.created_at).toLocaleString()}
              </td>
              <td>
                <div className="action-buttons">
                  {onEdit && (
                    <button 
                      className="action-btn edit"
                      onClick={() => onEdit(server)}
                      title="Edit server"
                    >
                      Edit
                    </button>
                  )}
                  {onDelete && (
                    <button 
                      className="action-btn delete"
                      onClick={() => onDelete(server.id)}
                      title="Delete server"
                    >
                      Delete
                    </button>
                  )}
                  {!onEdit && !onDelete && (
                    <span style={{ color: '#94a3b8', fontSize: '13px' }}>Read Only</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ServerTable;