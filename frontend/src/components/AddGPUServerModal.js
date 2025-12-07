import React, { useState, useEffect, useRef } from 'react';
import { getAllAzureUsers, getUserByEmail } from '../services/api';
import '../styles/components/Modal.css';

const AddGPUServerModal = ({ isOpen, onClose, onSuccess, editServer }) => {
  const [formData, setFormData] = useState({
    server_ip: '',
    server_name: '',
    username: '',
    port: '',
    rsa_key: '',
    rsa_key_passphrase: '',
    server_location: '',
    gpu_name: '',
    usage_limit: 80
  });
  
  const [alertEmails, setAlertEmails] = useState([]);
  const [currentEmail, setCurrentEmail] = useState('');
  const [showEmailList, setShowEmailList] = useState(false);
  const [emailSuggestions, setEmailSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [userPhotos, setUserPhotos] = useState({});
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [allUsers, setAllUsers] = useState([]); // ✅ NEW: Store all users once
  const [usersLoading, setUsersLoading] = useState(false);
  const suggestionRef = useRef(null);

  useEffect(() => {
    if (editServer) {
      setFormData({
        server_ip: editServer.server_ip || '',
        server_name: editServer.server_name || '',
        username: editServer.username || '',
        port: editServer.port || '',
        rsa_key: editServer.rsa_key || '',
        rsa_key_passphrase: editServer.rsa_key_passphrase || '',
        server_location: editServer.server_location || '',
        gpu_name: editServer.gpu_name || '',
        usage_limit: editServer.usage_limit || 80
      });
      setAlertEmails(editServer.alert_emails || []);
    } else {
      setFormData({
        server_ip: '',
        server_name: '',
        username: '',
        port: '',
        rsa_key: '',
        rsa_key_passphrase: '',
        server_location: '',
        gpu_name: '',
        usage_limit: 80
      });
      setAlertEmails([]);
    }
    setCurrentEmail('');
    setShowEmailList(false);
    setErrors({});
  }, [editServer, isOpen]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.server_ip.trim()) {
      newErrors.server_ip = 'Server IP is required';
    }

    if (!formData.server_name.trim()) {
      newErrors.server_name = 'Server name is required';
    }

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }

    if (!formData.port || formData.port < 1 || formData.port > 65535) {
      newErrors.port = 'Port must be between 1 and 65535';
    }

    if (!formData.rsa_key.trim()) {
      newErrors.rsa_key = 'RSA Key is required';
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
      const { createGPUServer, updateGPUServer } = require('../services/api');
      
      const dataToSubmit = {
        ...formData,
        port: parseInt(formData.port),
        usage_limit: parseInt(formData.usage_limit),
        rsa_key_passphrase: formData.rsa_key_passphrase.trim() || null,
        alert_emails: alertEmails
      };

      if (editServer) {
        await updateGPUServer(editServer.id, dataToSubmit);
      } else {
        await createGPUServer(dataToSubmit);
      }

      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error saving GPU server:', error);
      setErrors({ submit: error.response?.data?.detail || 'Failed to save GPU server' });
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

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target.result;
        
        setFormData(prev => ({
          ...prev,
          rsa_key: content
        }));
        
        // Clear error
        if (errors.rsa_key) {
          setErrors(prev => ({
            ...prev,
            rsa_key: ''
          }));
        }
      };
      reader.readAsText(file);
    }
  };


  const addEmail = () => {
    const email = currentEmail.trim();
    if (email) {
      // Validate email format
      if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        setErrors(prev => ({ ...prev, email: 'Invalid email format' }));
        return;
      }
      
      // Check for duplicates
      if (alertEmails.includes(email)) {
        setErrors(prev => ({ ...prev, email: 'Email already added' }));
        return;
      }
      
      setAlertEmails([...alertEmails, email]);
      setCurrentEmail('');
      setShowSuggestions(false);
      setEmailSuggestions([]);
      setErrors(prev => ({ ...prev, email: '' }));
    }
  };

  const removeEmail = (emailToRemove) => {
    setAlertEmails(alertEmails.filter(email => email !== emailToRemove));
  };

  const toggleEmailList = () => {
    setShowEmailList(!showEmailList);
  };

  useEffect(() => {
    // Handle click outside to close suggestions
    const handleClickOutside = (event) => {
      if (suggestionRef.current && !suggestionRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    // Fetch user photos for alert emails in PARALLEL for speed
    const fetchUserPhotos = async () => {
      if (alertEmails.length === 0) return;

      // Get emails that need fetching
      const emailsToFetch = alertEmails.filter(email => !userPhotos[email]);
      if (emailsToFetch.length === 0) return;

      // Fetch all photos in parallel using Promise.all
      const photoPromises = emailsToFetch.map(email =>
        getUserByEmail(email)
          .then(response => ({ email, user: response.data.user }))
          .catch(error => {
            console.error(`Failed to fetch user info for ${email}:`, error);
            return { email, user: null };
          })
      );

      const results = await Promise.all(photoPromises);
      
      // Build newPhotos object from results
      const newPhotos = {};
      results.forEach(({ email, user }) => {
        if (user) {
          newPhotos[email] = user;
        }
      });

      if (Object.keys(newPhotos).length > 0) {
        setUserPhotos(prev => ({ ...prev, ...newPhotos }));
      }
    };

    fetchUserPhotos();
  }, [alertEmails]);

  // ✅ NEW: Load all users once when modal opens
  useEffect(() => {
    const loadAllUsers = async () => {
      if (isOpen && allUsers.length === 0) {
        setUsersLoading(true);
        try {
          const response = await getAllAzureUsers();
          setAllUsers(response.data.users || []);
        } catch (error) {
          console.error('Error loading all users:', error);
        } finally {
          setUsersLoading(false);
        }
      }
    };

    loadAllUsers();
  }, [isOpen]);

  // ✅ NEW: Fetch photos for visible suggestions
  const [suggestionPhotos, setSuggestionPhotos] = useState({});
  useEffect(() => {
    const fetchSuggestionPhotos = async () => {
      if (emailSuggestions.length === 0) return;

      const photosToFetch = emailSuggestions.filter(user => !suggestionPhotos[user.email]);
      if (photosToFetch.length === 0) return;

      const photoPromises = photosToFetch.map(async (user) => {
        try {
          const response = await getUserByEmail(user.email);
          return { email: user.email, photoUrl: response.data.user?.photoUrl };
        } catch (error) {
          return { email: user.email, photoUrl: null };
        }
      });

      const results = await Promise.all(photoPromises);
      const newPhotos = {};
      results.forEach(({ email, photoUrl }) => {
        newPhotos[email] = photoUrl;
      });
      
      setSuggestionPhotos(prev => ({ ...prev, ...newPhotos }));
    };

    fetchSuggestionPhotos();
  }, [emailSuggestions]);

  // ✅ NEW: INSTANT client-side filtering - NO API calls!
  const handleEmailInputChange = (e) => {
    const value = e.target.value;
    setCurrentEmail(value);

    // Clear error if exists
    if (errors.email) {
      setErrors(prev => ({ ...prev, email: '' }));
    }

    // Clear suggestions if input is too short
    if (value.trim().length < 2) {
      setEmailSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const lowerValue = value.toLowerCase().trim();
    
    // ⚡ INSTANT local filtering (0ms response time!)
    const filtered = allUsers.filter(user => {
      const email = (user.email || '').toLowerCase();
      const displayName = (user.displayName || '').toLowerCase();
      return email.includes(lowerValue) || displayName.includes(lowerValue);
    });
    
    // Limit to 10 suggestions for better UX
    setEmailSuggestions(filtered.slice(0, 10));
    setShowSuggestions(filtered.length > 0);
  };

  const handleSelectSuggestion = (user) => {
    if (!alertEmails.includes(user.email)) {
      setAlertEmails([...alertEmails, user.email]);
    }
    setCurrentEmail('');
    setShowSuggestions(false);
    setEmailSuggestions([]);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            {editServer ? 'Edit GPU Server' : 'Add New GPU Server'}
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

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  Server IP <span className="required">*</span>
                </label>
                <input
                  type="text"
                  name="server_ip"
                  className={`form-input ${errors.server_ip ? 'error' : ''}`}
                  value={formData.server_ip}
                  onChange={handleChange}
                  placeholder="e.g., localhost or example.com"
                />
                {errors.server_ip && (
                  <span className="error-message">{errors.server_ip}</span>
                )}
              </div>

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
                  placeholder="e.g., GPU Server 1"
                />
                {errors.server_name && (
                  <span className="error-message">{errors.server_name}</span>
                )}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  Username <span className="required">*</span>
                </label>
                <input
                  type="text"
                  name="username"
                  className={`form-input ${errors.username ? 'error' : ''}`}
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="e.g., admin"
                />
                {errors.username && (
                  <span className="error-message">{errors.username}</span>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">
                  Port <span className="required">*</span>
                </label>
                <input
                  type="number"
                  name="port"
                  className={`form-input ${errors.port ? 'error' : ''}`}
                  value={formData.port}
                  onChange={handleChange}
                  placeholder="e.g., 22"
                  min="1"
                  max="65535"
                />
                {errors.port && (
                  <span className="error-message">{errors.port}</span>
                )}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Server Location</label>
                <input
                  type="text"
                  name="server_location"
                  className="form-input"
                  value={formData.server_location}
                  onChange={handleChange}
                  placeholder="e.g., Data Center A"
                />
              </div>

              <div className="form-group">
                <label className="form-label">GPU Name</label>
                <input
                  type="text"
                  name="gpu_name"
                  className="form-input"
                  value={formData.gpu_name}
                  onChange={handleChange}
                  placeholder="e.g., NVIDIA A100"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  RSA Key <span className="required">*</span>
                </label>
                <input
                  type="file"
                  accept="*"
                  onChange={handleFileUpload}
                  className={`form-input ${errors.rsa_key ? 'error' : ''}`}
                  style={{ padding: '8px' }}
                />
                <span style={{ fontSize: '12px', color: '#666', display: 'block', marginTop: '5px' }}>
                  Upload your RSA private key file (text file, e.g., RSA_key or id_rsa)
                </span>
                {formData.rsa_key && (
                  <div style={{ marginTop: '10px', padding: '8px', backgroundColor: '#f0f0f0', borderRadius: '4px', fontSize: '12px' }}>
                    ✓ Key loaded ({formData.rsa_key.length} characters)
                  </div>
                )}
                {errors.rsa_key && (
                  <span className="error-message">{errors.rsa_key}</span>
                )}
              </div>

              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">
                  Alert Emails
                  {alertEmails.length > 0 && (
                    <span style={{ fontSize: '12px', color: '#6b7280', marginLeft: '8px' }}>
                      ({alertEmails.length} added)
                    </span>
                  )}
                </label>
                <div style={{ position: 'relative' }} ref={suggestionRef}>
                  <input
                    type="text"
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    value={currentEmail}
                    onChange={handleEmailInputChange}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        // If suggestions are showing, select the first one
                        if (showSuggestions && emailSuggestions.length > 0) {
                          handleSelectSuggestion(emailSuggestions[0]);
                        } else {
                          // Otherwise, add the email manually
                          addEmail();
                        }
                      }
                    }}
                    placeholder="Search users or enter email..."
                    style={{ paddingRight: '35px' }}
                  />
                  <button
                    type="button"
                    onClick={toggleEmailList}
                    title={showEmailList ? "Hide email list" : "Show added emails"}
                    style={{
                      position: 'absolute',
                      right: '8px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '14px',
                      color: '#6b7280',
                      padding: '4px',
                      lineHeight: '1'
                    }}
                  >
                    {showEmailList ? '▲' : '▼'}
                  </button>
                  {errors.email && (
                    <span className="error-message">{errors.email}</span>
                  )}

                  {/* Email Suggestions Dropdown */}
                  {showSuggestions && emailSuggestions.length > 0 && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      marginTop: '4px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      backgroundColor: '#fff',
                      maxHeight: '200px',
                      overflowY: 'auto',
                      zIndex: 1000,
                      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}>
                      {emailSuggestions.map((user) => (
                        <div
                          key={user.id}
                          onClick={() => handleSelectSuggestion(user)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            padding: '8px 12px',
                            cursor: 'pointer',
                            borderBottom: '1px solid #e5e7eb',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                        >
                          <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            overflow: 'hidden',
                            marginRight: '10px',
                            flexShrink: 0,
                            backgroundColor: suggestionPhotos[user.email] ? 'transparent' : '#3b82f6',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#fff',
                            fontSize: '14px',
                            fontWeight: '600'
                          }}>
                            {suggestionPhotos[user.email] ? (
                              <img
                                src={suggestionPhotos[user.email]}
                                alt={user.displayName}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  e.target.parentElement.style.backgroundColor = '#3b82f6';
                                  e.target.parentElement.textContent = user.displayName?.charAt(0)?.toUpperCase() || '?';
                                }}
                              />
                            ) : (
                              user.displayName?.charAt(0)?.toUpperCase() || user.email?.charAt(0)?.toUpperCase() || '?'
                            )}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '14px', fontWeight: '600', color: '#1f2937', marginBottom: '2px', lineHeight: '1.4' }}>
                              {user.displayName}
                            </div>
                            <div style={{ fontSize: '12px', color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '0', lineHeight: '1.4' }}>
                              {user.email}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {showEmailList && alertEmails.length > 0 && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      marginTop: showSuggestions && emailSuggestions.length > 0 ? '210px' : '4px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      backgroundColor: '#fff',
                      maxHeight: '150px',
                      overflowY: 'auto',
                      zIndex: 10,
                      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}>
                      {alertEmails.map((email, index) => {
                        const user = userPhotos[email];
                        const hasPhoto = user && user.photoUrl;
                        return (
                          <div
                            key={index}
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '8px 12px',
                              borderBottom: index < alertEmails.length - 1 ? '1px solid #e5e7eb' : 'none',
                              fontSize: '14px'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {hasPhoto && (
                                <img
                                  src={user.photoUrl}
                                  alt={user.displayName || email}
                                  style={{
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '50%',
                                    objectFit: 'cover'
                                  }}
                                />
                              )}
                              {!hasPhoto && (
                                <div style={{
                                  width: '28px',
                                  height: '28px',
                                  borderRadius: '50%',
                                  backgroundColor: '#3b82f6',
                                  color: '#fff',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: '12px',
                                  fontWeight: '600'
                                }}>
                                  {(user?.displayName || email).charAt(0).toUpperCase()}
                                </div>
                              )}
                              <span style={{ color: '#374151' }}>{user?.displayName || email}</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeEmail(email)}
                              title="Remove email"
                              style={{
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '18px',
                                color: '#9ca3af',
                                padding: '0 4px',
                                lineHeight: '1'
                              }}
                            >
                              ×
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  RSA Passphrase
                </label>
                <input
                  type="password"
                  name="rsa_key_passphrase"
                  className={`form-input ${errors.rsa_key_passphrase ? 'error' : ''}`}
                  value={formData.rsa_key_passphrase}
                  onChange={handleChange}
                  placeholder="Enter passphrase (optional)"
                />
                {errors.rsa_key_passphrase && (
                  <span className="error-message">{errors.rsa_key_passphrase}</span>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">GPU Memory Usage Limit (%)</label>
                <input
                  type="number"
                  name="usage_limit"
                  className="form-input"
                  value={formData.usage_limit}
                  onChange={handleChange}
                  min="0"
                  max="100"
                  placeholder="e.g., 80"
                />
              </div>
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

export default AddGPUServerModal;