import React, { useState, useEffect, useRef } from 'react';
import { getAllAzureUsers } from '../services/api';
import '../styles/components/Modal.css';

const AddEmailAlertModal = ({ isOpen, onClose, onSave, url, urls = [], onUrlSelect }) => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [emailSuggestions, setEmailSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [allUsers, setAllUsers] = useState([]); // ✅ NEW: Store all users once
  const [usersLoading, setUsersLoading] = useState(false);
  const suggestionRef = useRef(null);
  const [selectedUrl, setSelectedUrl] = useState(url);

  useEffect(() => {
    setSelectedUrl(url);
  }, [url]);

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

  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  // ✅ NEW: INSTANT client-side filtering - NO API calls!
  const handleEmailInputChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setError('');

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
      const alreadyAdded = selectedUrl?.alert_emails?.includes(user.email);
      
      return !alreadyAdded && (email.includes(lowerValue) || displayName.includes(lowerValue));
    });
    
    // Limit to 10 suggestions for better UX
    setEmailSuggestions(filtered.slice(0, 10));
    setShowSuggestions(filtered.length > 0);
  };

  const handleSelectUrl = (e) => {
    const urlId = parseInt(e.target.value);
    const selected = urls.find(u => u.id === urlId);
    setSelectedUrl(selected);
    if (onUrlSelect) {
      onUrlSelect(selected);
    }
  };

  const handleSelectSuggestion = (user) => {
    if (!selectedUrl) {
      setError('Please select a project first');
      return;
    }

    // Check if email already exists
    if (selectedUrl?.alert_emails?.includes(user.email)) {
      setError('This email is already added');
      return;
    }

    onSave(user.email);
    setEmail('');
    setEmailSuggestions([]);
    setShowSuggestions(false);
    onClose();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!selectedUrl) {
      setError('Please select a project first');
      return;
    }

    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    // Check if email already exists
    if (selectedUrl?.alert_emails?.includes(email)) {
      setError('This email is already added');
      return;
    }

    onSave(email);
    setEmail('');
    setEmailSuggestions([]);
    setShowSuggestions(false);
    onClose();
  };

  const handleClose = () => {
    setEmail('');
    setError('');
    setEmailSuggestions([]);
    setShowSuggestions(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Email Alert</h2>
          <button className="modal-close" onClick={handleClose}>&times;</button>
        </div>

        <div className="modal-body">
          {!url && urls.length > 0 && (
            <div className="form-group">
              <label htmlFor="project">Select Project</label>
              <select 
                id="project"
                value={selectedUrl?.id || ''}
                onChange={handleSelectUrl}
                className="form-select"
              >
                <option value="">Choose a project...</option>
                {urls.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.project_name} ({u.environment})
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedUrl && (
            <p className="modal-description">
              Add an email address to receive alerts for: <strong>{selectedUrl.project_name}</strong>
            </p>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <div className="email-input-container" ref={suggestionRef}>
                <input
                  type="text"
                  id="email"
                  value={email}
                  onChange={handleEmailInputChange}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && showSuggestions && emailSuggestions.length > 0) {
                      e.preventDefault();
                      // Select first suggestion on Enter
                      handleSelectSuggestion(emailSuggestions[0]);
                    }
                  }}
                  placeholder="Search users or enter email..."
                  className={error ? 'error' : ''}
                  autoFocus
                  autoComplete="off"
                />
                {showSuggestions && emailSuggestions.length > 0 && (
                  <div className="email-suggestions">
                    {emailSuggestions.map((user) => (
                      <div
                        key={user.id}
                        className="email-suggestion-item"
                        onClick={() => handleSelectSuggestion(user)}
                      >
                        <div className="user-avatar">
                          {suggestionPhotos[user.email] ? (
                            <img
                              src={suggestionPhotos[user.email]}
                              alt={user.displayName}
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.parentElement.querySelector('.user-avatar-placeholder').style.display = 'flex';
                              }}
                            />
                          ) : null}
                          <div
                            className="user-avatar-placeholder"
                            style={{ display: suggestionPhotos[user.email] ? 'none' : 'flex' }}
                          >
                            {user.displayName.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div className="user-info">
                          <div className="user-name">{user.displayName}</div>
                          <div className="user-email">{user.email}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {error && <span className="error-message">{error}</span>}
            </div>

            {selectedUrl?.alert_emails && selectedUrl.alert_emails.length > 0 && (
              <div className="current-emails">
                <label>Current Email Alerts:</label>
                <div className="email-list">
                  {selectedUrl.alert_emails.map((existingEmail, index) => (
                    <span key={index} className="email-badge">{existingEmail}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={handleClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Add Email
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddEmailAlertModal;