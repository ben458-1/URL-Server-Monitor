import React, { useState, useEffect, useRef } from 'react';
import { getServersByGPUName, updateUsageLimit, updateAlertEmails, getAllAzureUsers, getUserByEmail } from '../services/api';
import '../styles/components/ManageGPUModal.css';

function ManageGPUModal({ gpuName, isOpen, onClose, onUpdate, buttonRef, azureUsersCache }) {
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [usageLimit, setUsageLimit] = useState(80);
  const [alertEmails, setAlertEmails] = useState([]);
  const [emailInput, setEmailInput] = useState('');
  const [emailSuggestions, setEmailSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [position, setPosition] = useState({ top: 0, right: 0 });
  const [userPhotos, setUserPhotos] = useState({});
  const suggestionRef = useRef(null);
  const panelRef = useRef(null);
  
  // Use cached Azure users from props instead of loading them
  const allUsers = azureUsersCache?.users || [];
  const usersLoading = azureUsersCache?.isLoading || false;

  // Calculate position based on button location (fixed positioning with viewport bounds)
  useEffect(() => {
    const updatePosition = () => {
      if (isOpen && buttonRef?.current) {
        const buttonRect = buttonRef.current.getBoundingClientRect();
        const panelWidth = 320;
        const spacing = 8;
        
        // Default: align right edge of panel with right edge of button
        let left = buttonRect.right - panelWidth;
        let top = buttonRect.bottom + spacing;
        
        // Ensure panel doesn't overflow right edge of viewport
        if (left + panelWidth > window.innerWidth - spacing) {
          left = window.innerWidth - panelWidth - spacing;
        }
        
        // Ensure panel doesn't overflow left edge of viewport
        if (left < spacing) {
          left = spacing;
        }
        
        // Ensure panel doesn't overflow bottom of viewport (if needed, show above button)
        const panelHeight = 450; // Approximate
        if (top + panelHeight > window.innerHeight && buttonRect.top - panelHeight - spacing > 0) {
          top = buttonRect.top - panelHeight - spacing;
        }
        
        setPosition({ top, left });
      }
    };

    updatePosition();
    
    // Update position on scroll and resize to keep it aligned with button
    window.addEventListener('scroll', updatePosition, true);
    window.addEventListener('resize', updatePosition);
    
    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isOpen, buttonRef]);

  useEffect(() => {
    if (isOpen && gpuName) {
      loadServers();
    }
  }, [isOpen, gpuName]);

  useEffect(() => {
    // Handle click outside to close panel
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target) && 
          buttonRef?.current && !buttonRef.current.contains(event.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose, buttonRef]);

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

  const loadServers = async () => {
    try {
      setLoading(true);
      const response = await getServersByGPUName(gpuName);
      setServers(response.data);
      
      // Select the first server by default
      if (response.data.length > 0) {
        selectServer(response.data[0]);
      }
    } catch (error) {
      console.error('Error loading servers:', error);
      setError('Failed to load server information');
    } finally {
      setLoading(false);
    }
  };

  const selectServer = (server) => {
    setSelectedServer(server);
    setUsageLimit(server.usage_limit || 80);
    setAlertEmails(server.alert_emails || []);
  };

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

  // Fetch photos for visible suggestions
  useEffect(() => {
    const fetchSuggestionPhotos = async () => {
      if (emailSuggestions.length === 0) return;

      // Fetch photos for suggestions we don't have yet
      const photosToFetch = emailSuggestions.filter(user => !userPhotos[user.email]);
      
      if (photosToFetch.length === 0) return;

      // Fetch in parallel (max 10 suggestions shown anyway)
      const photoPromises = photosToFetch.map(async (user) => {
        try {
          const response = await getUserByEmail(user.email);
          return { email: user.email, photoUrl: response.data.user?.photoUrl };
        } catch (error) {
          return { email: user.email, photoUrl: null };
        }
      });

      const results = await Promise.all(photoPromises);
      
      // Update photos state
      const newPhotos = {};
      results.forEach(({ email, photoUrl }) => {
        newPhotos[email] = photoUrl;
      });
      
      setUserPhotos(prev => ({ ...prev, ...newPhotos }));
    };

    fetchSuggestionPhotos();
  }, [emailSuggestions]);

  // ✅ NEW: INSTANT client-side filtering - NO API calls!
  const handleEmailInputChange = (e) => {
    const value = e.target.value;
    setEmailInput(value);

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
    setEmailInput('');
    setShowSuggestions(false);
    setEmailSuggestions([]);
  };

  const handleAddEmail = (e) => {
    e.preventDefault();
    const email = emailInput.trim();
    
    if (email && isValidEmail(email) && !alertEmails.includes(email)) {
      setAlertEmails([...alertEmails, email]);
      setEmailInput('');
      setShowSuggestions(false);
    }
  };

  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleRemoveEmail = (emailToRemove) => {
    setAlertEmails(alertEmails.filter(email => email !== emailToRemove));
  };

  const handleSave = async () => {
    if (!selectedServer) return;

    try {
      setSaving(true);
      setError(null);

      // Update usage limit
      await updateUsageLimit(selectedServer.id, usageLimit);
      
      // Update alert emails
      await updateAlertEmails(selectedServer.id, alertEmails);

      // Notify parent component
      if (onUpdate) {
        onUpdate();
      }

      onClose();
    } catch (error) {
      console.error('Error saving settings:', error);
      setError('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="manage-gpu-panel" 
      ref={panelRef}
      style={{ 
        top: `${position.top}px`,
        left: `${position.left}px`
      }}
    >
      <div className="panel-container">
        <div className="panel-header">
          <h3>GPU Settings</h3>
          <button className="close-panel-button" onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="panel-body">
          {loading ? (
            <div className="loading-message">Loading...</div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : (
            <div className="compact-form">
              <div className="compact-section">
                <label className="compact-label">GPU Memory Usage Limit (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={usageLimit}
                  onChange={(e) => {
                    const val = parseInt(e.target.value) || 0;
                    if (val >= 0 && val <= 100) {
                      setUsageLimit(val);
                    }
                  }}
                  className="compact-input"
                  placeholder="0-100"
                />
              </div>

              <div className="compact-section email-section">
                <label className="compact-label">Alert Emails</label>
                <div className="email-input-container" ref={suggestionRef}>
                  <input
                    type="text"
                    value={emailInput}
                    onChange={handleEmailInputChange}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                      }
                    }}
                    placeholder="Search users..."
                    className="compact-input"
                  />

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
                            backgroundColor: userPhotos[user.email] ? 'transparent' : '#3b82f6',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#fff',
                            fontSize: '14px',
                            fontWeight: '600'
                          }}>
                            {userPhotos[user.email] ? (
                              <img
                                src={userPhotos[user.email]}
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
                </div>

                <div className="email-avatars">
                  {alertEmails.map((email, index) => {
                    const user = userPhotos[email];
                    const hasPhoto = user && user.photoUrl;
                    
                    return (
                      <div key={index} className="email-avatar-item" title={user?.displayName || email}>
                        {hasPhoto && (
                          <img
                            src={user.photoUrl}
                            alt={user.displayName || email}
                            className="avatar-image"
                          />
                        )}
                        <div
                          className="avatar-circle"
                          style={{ display: hasPhoto ? 'none' : 'flex' }}
                        >
                          {(user?.displayName || email).charAt(0).toUpperCase()}
                        </div>
                        <button
                          onClick={() => handleRemoveEmail(email)}
                          className="remove-avatar-button"
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="panel-footer">
          <button
            className="save-button"
            onClick={handleSave}
            disabled={saving || loading || !selectedServer}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button className="cancel-button" onClick={onClose} disabled={saving}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default ManageGPUModal;

