import React, { useState, useEffect } from 'react';
import '../styles/components/Modal.css';

const AddServerModal = ({ isOpen, onClose, onSuccess, editServer }) => {
  const [formData, setFormData] = useState({
    server_name: '',
    port: '',
    server_location: 'India'
  });
  
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (editServer) {
      setFormData({
        server_name: editServer.server_name || '',
        port: editServer.port || '',
        server_location: editServer.server_location || 'India'
      });
    } else {
      setFormData({
        server_name: '',
        port: '',
        server_location: 'India'
      });
    }
    setErrors({});
  }, [editServer, isOpen]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.server_name.trim()) {
      newErrors.server_name = 'Server name is required';
    }

    if (formData.port && (formData.port < 1 || formData.port > 65535)) {
      newErrors.port = 'Port must be between 1 and 65535';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const { createServer, updateServer } = require('../services/api');
      
      const dataToSubmit = {
        ...formData,
        port: formData.port ? parseInt(formData.port) : null
      };

      if (editServer) {
        await updateServer(editServer.id, dataToSubmit);
      } else {
        await createServer(dataToSubmit);
      }

      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error saving server:', error);
      setErrors({ submit: error.response?.data?.detail || 'Failed to save server' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            {editServer ? 'Edit Server' : 'Add New Server'}
          </h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.submit && (
              <div className="error-message" style={{ marginBottom: '16px', padding: '12px', background: '#fee', borderRadius: '6px', color: '#c00' }}>
                {errors.submit}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">
                Server Name <span className="required">*</span>
              </label>
              <input
                type="text"
                name="server_name"
                className={`form-input ${errors.server_name ? 'error' : ''}`}
                value={formData.server_name}
                onChange={handleChange}
                placeholder="e.g., Production Server, Dev Server"
              />
              {errors.server_name && (
                <span className="error-message">{errors.server_name}</span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Port</label>
              <input
                type="number"
                name="port"
                className={`form-input ${errors.port ? 'error' : ''}`}
                value={formData.port}
                onChange={handleChange}
                placeholder="e.g., 8080 (optional)"
                min="1"
                max="65535"
              />
              {errors.port && (
                <span className="error-message">{errors.port}</span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">
                Server Location <span className="required">*</span>
              </label>
              <select
                name="server_location"
                className="form-select"
                value={formData.server_location}
                onChange={handleChange}
              >
                <option value="India">India</option>
                <option value="Estonia">Estonia</option>
              </select>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : (editServer ? 'Update Server' : 'Add Server')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddServerModal;