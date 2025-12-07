import React, { useState, useEffect } from 'react';
import { createUrl, updateUrl, getAllProjects, createProject } from '../services/api';
import '../styles/components/Modal.css';

const AddURLModal = ({ isOpen, onClose, onSuccess, editUrl, servers = [] }) => {
  const [formData, setFormData] = useState({
    project_name: '',
    url: '',
    environment: '',
    project_category: '',
    server_id: '',
    description: ''
  });

  const [projects, setProjects] = useState([]);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadProjects();
      if (editUrl) {
        setFormData({
          project_name: editUrl.project_name || '',
          url: editUrl.url || '',
          environment: editUrl.environment || '',
          project_category: editUrl.project_category || '',
          server_id: editUrl.server_id || '',
          description: editUrl.description || ''
        });
      } else {
        resetForm();
      }
    }
  }, [isOpen, editUrl]);

  const loadProjects = async () => {
    try {
      const response = await getAllProjects();
      setProjects(response.data);
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      project_name: '',
      url: '',
      environment: '',
      project_category: '',
      server_id: '',
      description: ''
    });
    setErrors({});
    setShowNewProject(false);
    setNewProjectName('');
  };

  const handleServerChange = (e) => {
    const serverId = e.target.value;
    
    setFormData(prev => ({
      ...prev,
      server_id: serverId
    }));
    
    // Clear errors
    setErrors(prev => ({
      ...prev,
      server_id: ''
    }));
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

  const handleProjectCategoryChange = (e) => {
    const value = e.target.value;
    if (value === '__new__') {
      setShowNewProject(true);
      setFormData(prev => ({
        ...prev,
        project_category: ''
      }));
    } else {
      setShowNewProject(false);
      setFormData(prev => ({
        ...prev,
        project_category: value
      }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.project_name.trim()) {
      newErrors.project_name = 'Project name is required';
    }

    if (!formData.url.trim()) {
      newErrors.url = 'URL is required';
    } else {
      try {
        new URL(formData.url);
      } catch {
        newErrors.url = 'Invalid URL format';
      }
    }

    if (!formData.environment) {
      newErrors.environment = 'Environment is required';
    }

    if (!formData.server_id) {
      newErrors.server_id = 'Server is required';
    }

    if (showNewProject && !newProjectName.trim()) {
      newErrors.newProjectName = 'New project category name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setLoading(true);

    try {
      let finalProjectCategory = formData.project_category;

      // Create new project if needed
      if (showNewProject && newProjectName.trim()) {
        const projectResponse = await createProject(newProjectName.trim());
        finalProjectCategory = projectResponse.data.name;
      }

      const submitData = {
        ...formData,
        project_category: finalProjectCategory || null,
        server_id: formData.server_id ? parseInt(formData.server_id) : null
      };

      if (editUrl) {
        await updateUrl(editUrl.id, submitData);
      } else {
        await createUrl(submitData);
      }

      onSuccess();
      onClose();
      resetForm();
    } catch (error) {
      console.error('Error saving URL:', error);
      alert(error.response?.data?.detail || 'Failed to save URL');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{editUrl ? 'Edit URL' : 'Add New URL'}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">
                Project Name <span className="required">*</span>
              </label>
              <input
                type="text"
                name="project_name"
                className={`form-input ${errors.project_name ? 'error' : ''}`}
                value={formData.project_name}
                onChange={handleChange}
                placeholder="Enter project name"
              />
              {errors.project_name && <span className="error-message">{errors.project_name}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                URL <span className="required">*</span>
              </label>
              <input
                type="text"
                name="url"
                className={`form-input ${errors.url ? 'error' : ''}`}
                value={formData.url}
                onChange={handleChange}
                placeholder="https://example.com"
              />
              {errors.url && <span className="error-message">{errors.url}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                Environment <span className="required">*</span>
              </label>
              <select
                name="environment"
                className={`form-select ${errors.environment ? 'error' : ''}`}
                value={formData.environment}
                onChange={handleChange}
              >
                <option value="">Select environment</option>
                <option value="production">Production</option>
                <option value="development">Development</option>
                <option value="staging">Staging</option>
              </select>
              {errors.environment && <span className="error-message">{errors.environment}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Project Category</label>
              <select
                className="form-select"
                value={showNewProject ? '__new__' : formData.project_category}
                onChange={handleProjectCategoryChange}
              >
                <option value="">Select project category</option>
                {projects.map(project => (
                  <option key={project.id} value={project.name}>{project.name}</option>
                ))}
                <option value="__new__">+ Add New Category</option>
              </select>
            </div>

            {showNewProject && (
              <div className="new-project-section">
                <div className="form-group">
                  <label className="form-label">New Category Name</label>
                  <input
                    type="text"
                    className={`form-input ${errors.newProjectName ? 'error' : ''}`}
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    placeholder="Enter category name"
                  />
                  {errors.newProjectName && <span className="error-message">{errors.newProjectName}</span>}
                </div>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">
                Server <span className="required">*</span>
              </label>
              <select
                name="server_id"
                className={`form-select ${errors.server_id ? 'error' : ''}`}
                value={formData.server_id}
                onChange={handleServerChange}
              >
                <option value="">Select server</option>
                {servers.map(server => (
                  <option key={server.id} value={server.id}>
                    {server.server_name} {server.port ? `(Port: ${server.port})` : ''} - {server.server_location}
                  </option>
                ))}
              </select>
              {errors.server_id && <span className="error-message">{errors.server_id}</span>}
            </div>

            {formData.server_id && (() => {
              const selectedServer = servers.find(s => s.id === parseInt(formData.server_id));
              return selectedServer ? (
                <div className="server-info-box" style={{
                  padding: '12px 16px',
                  background: '#f0f9ff',
                  border: '1px solid #bae6fd',
                  borderRadius: '8px',
                  marginBottom: '16px'
                }}>
                  <div style={{ fontSize: '14px', color: '#374151', fontWeight: '600', marginBottom: '8px' }}>
                    Server Details
                  </div>
                  <div style={{ fontSize: '13px', color: '#0c4a6e' }}>
                    <div><strong>Server Name:</strong> {selectedServer.server_name}</div>
                    {selectedServer.port && <div><strong>Port:</strong> {selectedServer.port}</div>}
                    <div><strong>Location:</strong> {selectedServer.server_location}</div>
                  </div>
                </div>
              ) : null;
            })()}

            <div className="form-group">
              <label className="form-label">Description (Optional)</label>
              <textarea
                name="description"
                className="form-input"
                value={formData.description}
                onChange={handleChange}
                placeholder="Enter a description for this URL"
                rows="3"
                style={{ resize: 'vertical', minHeight: '60px' }}
              />
            </div>
          </form>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddURLModal;