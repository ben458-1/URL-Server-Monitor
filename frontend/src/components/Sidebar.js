import React, { useState, useEffect } from 'react';
import { useMsal } from '@azure/msal-react';
import '../styles/components/Sidebar.css';

const Sidebar = ({
  currentUser,
  activeSection,
  onSectionChange,
  activeEnvironment,
  onEnvironmentChange
}) => {
  const { instance, accounts } = useMsal();
  const [showHealthcheckDropdown, setShowHealthcheckDropdown] = useState(true);
  const [showEnvironmentDropdown, setShowEnvironmentDropdown] = useState(true);
  const [profilePhoto, setProfilePhoto] = useState(null);

  const environments = [
    { name: 'Production', value: 'production' },
    { name: 'Development', value: 'development' },
    { name: 'Staging', value: 'staging' }
  ];

  // Fetch Microsoft profile photo
  useEffect(() => {
    const fetchProfilePhoto = async () => {
      if (accounts.length > 0) {
        try {
          const response = await instance.acquireTokenSilent({
            scopes: ['User.Read'],
            account: accounts[0]
          });
          
          // Fetch profile photo from Microsoft Graph
          const photoResponse = await fetch('https://graph.microsoft.com/v1.0/me/photo/$value', {
            headers: {
              'Authorization': `Bearer ${response.accessToken}`
            }
          });
          
          if (photoResponse.ok) {
            const blob = await photoResponse.blob();
            const photoUrl = URL.createObjectURL(blob);
            setProfilePhoto(photoUrl);
          }
        } catch (error) {
          console.log('Could not fetch profile photo:', error);
          // Silently fail - will use initials instead
        }
      }
    };

    fetchProfilePhoto();

    // Cleanup function to revoke object URL
    return () => {
      if (profilePhoto) {
        URL.revokeObjectURL(profilePhoto);
      }
    };
  }, [accounts, instance]);

  const handleEnvironmentClick = (envValue) => {
    onSectionChange('healthcheck');
    onEnvironmentChange(envValue);
  };

  const handleLogout = () => {
    // Clear cached user data on logout
    localStorage.removeItem('currentUser');
    instance.logoutPopup({
      postLogoutRedirectUri: "/",
      mainWindowRedirectUri: "/"
    });
  };

  const getUserInitials = () => {
    if (currentUser && currentUser.user && currentUser.user.name) {
      return currentUser.user.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    }
    if (accounts.length > 0 && accounts[0].name) {
      return accounts[0].name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    }
    return '??';
  };

  const getUserName = () => {
    if (currentUser && currentUser.user && currentUser.user.name) {
      return currentUser.user.name;
    }
    if (accounts.length > 0 && accounts[0].name) {
      return accounts[0].name;
    }
    return 'User';
  };

  const getUserRole = () => {
    if (currentUser && currentUser.user && currentUser.user.role) {
      return currentUser.user.role;
    }
    return '';
  };

  return (
    <aside className="sidebar">
      <div className="user-profile">
        <div className="user-avatar">
          {profilePhoto ? (
            <img src={profilePhoto} alt="Profile" className="user-avatar-img" />
          ) : (
            getUserInitials()
          )}
        </div>
        <div className="user-info">
          <div className="user-name">{getUserName()}</div>
          <button className="logout-btn" onClick={handleLogout}>
            <svg 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span>Logout</span>
          </button>
        </div>
      </div>

      <nav className="nav-menu">
        <div
          className={`nav-item ${activeSection === 'healthcheck' ? 'active' : ''} has-dropdown`}
          onClick={() => setShowHealthcheckDropdown(!showHealthcheckDropdown)}
        >
          <span className="nav-icon"></span>
          <span className="nav-text">URL Healthcheck</span>
        </div>

        {showHealthcheckDropdown && (
          <div className="nav-submenu">
            {/* Environment submenu with dropdown */}
            <div
              className={`nav-subitem has-dropdown ${activeSection === 'healthcheck' ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                setShowEnvironmentDropdown(!showEnvironmentDropdown);
              }}
            >
              <span>Environment</span>
              <span className={`dropdown-arrow ${showEnvironmentDropdown ? 'open' : ''}`}>▶</span>
            </div>

            <div className={`nav-sub-submenu ${showEnvironmentDropdown ? 'open' : ''}`}>
              {environments.map(env => (
                <div
                  key={env.value}
                  className={`nav-sub-subitem ${activeSection === 'healthcheck' && activeEnvironment === env.value ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEnvironmentClick(env.value);
                  }}
                >
                  <span>{env.name}</span>
                </div>
              ))}
            </div>

            {/* Server */}
            <div
              className={`nav-subitem ${activeSection === 'server' ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                onSectionChange('server');
              }}
            >
              <span>Server</span>
            </div>
          </div>
        )}

        <div
          className={`nav-item ${activeSection === 'gpu-stats' ? 'active' : ''}`}
          onClick={() => onSectionChange('gpu-stats')}
        >
          <span className="nav-icon"></span>
          <span>GPU Statistics</span>
        </div>

        {currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor') && (
          <div
            className={`nav-item ${activeSection === 'user-management' ? 'active' : ''}`}
            onClick={() => onSectionChange('user-management')}
          >
            <span className="nav-icon"></span>
            <span>User Management</span>
          </div>
        )}
      </nav>
    </aside>
  );
};

export default Sidebar;