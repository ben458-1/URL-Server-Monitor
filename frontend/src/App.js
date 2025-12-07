import React, { useState, useEffect } from 'react';
import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from '@azure/msal-react';
import { loginRequest, loginRequestFallback } from './authConfig';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import CategoryDropdown from './components/CategoryDropdown';
import URLTable from './components/URLTable';
import AddURLModal from './components/AddURLModal';
import ServerTable from './components/ServerTable';
import AddServerModal from './components/AddServerModal';
import GPUStats from './components/GPUStats';
import UserManagement from './components/UserManagement';
import AddGPUServerModal from './components/AddGPUServerModal';
import api, { getAllUrls, deleteUrl as deleteUrlApi, getAllLatestHealth, getAllServers, deleteServer as deleteServerApi, configureAuth, getOverallGPUMetrics, getAllAzureUsers } from './services/api';
import websocketService from './services/websocket';
import './App.css';

function App() {
  const { instance, accounts } = useMsal();
  // Initialize currentUser from localStorage if available
  const [currentUser, setCurrentUser] = useState(() => {
    const cached = localStorage.getItem('currentUser');
    return cached ? JSON.parse(cached) : null;
  });
  const [authLoading, setAuthLoading] = useState(true);
  
  // Load saved section and environment from localStorage, or use defaults
  const [activeSection, setActiveSection] = useState(() => {
    const saved = localStorage.getItem('activeSection');
    return saved || 'healthcheck';
  });
  const [activeEnvironment, setActiveEnvironment] = useState(() => {
    const saved = localStorage.getItem('activeEnvironment');
    return saved || 'production';
  });
  const [activeCategory, setActiveCategory] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isServerModalOpen, setIsServerModalOpen] = useState(false);
  const [isGPUServerModalOpen, setIsGPUServerModalOpen] = useState(false);
  const [editUrl, setEditUrl] = useState(null);
  const [editServer, setEditServer] = useState(null);
  const [editGPUServer, setEditGPUServer] = useState(null);
  
  // Healthcheck data cache - persists across navigation and browser refresh
  const [healthcheckCache, setHealthcheckCache] = useState(() => {
    try {
      const cached = localStorage.getItem('healthcheckCache');
      if (cached) {
        const parsed = JSON.parse(cached);
        const cacheAge = Date.now() - (parsed.lastUpdated ? new Date(parsed.lastUpdated).getTime() : 0);
        // Use cache if less than 5 minutes old
        if (cacheAge < 5 * 60 * 1000) {
          return { ...parsed, lastUpdated: parsed.lastUpdated ? new Date(parsed.lastUpdated) : null };
        }
      }
    } catch (e) {
      console.error('Error loading healthcheck cache:', e);
    }
    return {
      urls: [],
      servers: [],
      healthStatuses: [],
      lastUpdated: null,
      isLoading: false
    };
  });
  
  // GPU metrics cache - persists across navigation and browser refresh
  const [gpuMetricsCache, setGpuMetricsCache] = useState(() => {
    try {
      const cached = localStorage.getItem('gpuMetricsCache');
      if (cached) {
        const parsed = JSON.parse(cached);
        const cacheAge = Date.now() - (parsed.lastUpdated ? new Date(parsed.lastUpdated).getTime() : 0);
        // Use cache if less than 5 minutes old
        if (cacheAge < 5 * 60 * 1000) {
          return { ...parsed, lastUpdated: parsed.lastUpdated ? new Date(parsed.lastUpdated) : null };
        }
      }
    } catch (e) {
      console.error('Error loading GPU metrics cache:', e);
    }
    return {
      overall: [],
      individual: [],
      lastUpdated: null,
      isLoading: false
    };
  });

  // User management cache - persists across navigation and browser refresh
  const [userManagementCache, setUserManagementCache] = useState(() => {
    try {
      const cached = localStorage.getItem('userManagementCache');
      if (cached) {
        const parsed = JSON.parse(cached);
        const cacheAge = Date.now() - (parsed.lastUpdated ? new Date(parsed.lastUpdated).getTime() : 0);
        // Use cache if less than 10 minutes old
        if (cacheAge < 10 * 60 * 1000) {
          return { ...parsed, lastUpdated: parsed.lastUpdated ? new Date(parsed.lastUpdated) : null };
        }
      }
    } catch (e) {
      console.error('Error loading user management cache:', e);
    }
    return {
      azureUsers: [],
      dbUsers: [],
      roles: [],
      lastUpdated: null,
      isLoading: false
    };
  });

  // Azure users cache for GPU settings modal - shared across the app
  const [azureUsersCache, setAzureUsersCache] = useState(() => {
    try {
      const cached = localStorage.getItem('azureUsersCache');
      if (cached) {
        const parsed = JSON.parse(cached);
        const cacheAge = Date.now() - (parsed.lastUpdated ? new Date(parsed.lastUpdated).getTime() : 0);
        // Use cache if less than 10 minutes old
        if (cacheAge < 10 * 60 * 1000) {
          return { ...parsed, lastUpdated: parsed.lastUpdated ? new Date(parsed.lastUpdated) : null };
        }
      }
    } catch (e) {
      console.error('Error loading Azure users cache:', e);
    }
    return {
      users: [],
      lastUpdated: null,
      isLoading: false
    };
  });

  // Save healthcheck cache to localStorage whenever it updates
  useEffect(() => {
    if (healthcheckCache.lastUpdated) {
      try {
        localStorage.setItem('healthcheckCache', JSON.stringify(healthcheckCache));
      } catch (e) {
        console.error('Error saving healthcheck cache:', e);
      }
    }
  }, [healthcheckCache]);

  useEffect(() => {
    const initializeAuth = async () => {
      console.log('🚀 Initializing authentication...', { accountsCount: accounts.length });
      
      if (accounts.length > 0) {
        try {
          console.log('👤 Account found:', accounts[0].username);
          
          // Configure API authentication to use MSAL token FIRST
          configureAuth(async () => {
            try {
              console.log('🔐 Attempting to acquire token for backend API...');
              const response = await instance.acquireTokenSilent({
                scopes: loginRequest.scopes,
                account: accounts[0]
              });
              console.log('✅ Token acquired successfully for backend API');
              console.log('Token details:', {
                scopes: loginRequest.scopes,
                expiresOn: response.expiresOn,
                account: response.account.username
              });
              return response.accessToken;
            } catch (error) {
              console.error('❌ Primary token acquisition failed:', error);
              console.log('Error details:', error.errorCode, error.errorMessage);
              
              // Try fallback scope (client ID directly)
              try {
                console.log('🔄 Attempting fallback token acquisition with client ID...');
                const fallbackResponse = await instance.acquireTokenSilent({
                  scopes: loginRequestFallback.scopes,
                  account: accounts[0]
                });
                console.log('✅ Fallback token acquired successfully');
                return fallbackResponse.accessToken;
              } catch (fallbackError) {
                console.error('❌ Fallback token acquisition failed:', fallbackError);
                
                // Try interactive login if silent fails
                try {
                  console.log('🔄 Attempting interactive token acquisition...');
                  const interactiveResponse = await instance.acquireTokenPopup({
                    scopes: loginRequest.scopes,
                    account: accounts[0]
                  });
                  console.log('✅ Interactive token acquired successfully');
                  return interactiveResponse.accessToken;
                } catch (popupError) {
                  console.error('❌ All token acquisition methods failed:', popupError);
                  return null;
                }
              }
            }
          });
          
          // Now make API calls after auth is configured
          console.log('📡 Fetching user data from backend...');
          await fetchCurrentUser();
          
          console.log('📡 Loading application data...');
          await loadUrls();
          await loadHealthStatuses();
          await loadServers();
          
          console.log('🔌 Connecting to WebSocket...');
          // Connect to WebSocket
          websocketService.connect();
          
          // Subscribe to WebSocket messages
          const unsubscribe = websocketService.subscribe(handleWebSocketMessage);
          
          console.log('✅ Initialization complete!');
          
          // Cleanup on unmount
          return () => {
            unsubscribe();
            websocketService.disconnect();
          };
        } catch (error) {
          console.error('❌ Initialization failed:', error);
          setAuthLoading(false);
        }
      } else {
        console.log('⚠️ No accounts found, showing login page');
        setAuthLoading(false);
      }
    };
    
    // Safety timeout to prevent infinite loading
    const timeout = setTimeout(() => {
      console.warn('⏰ Auth initialization timeout - forcing loading to false');
      setAuthLoading(false);
    }, 10000); // 10 second timeout
    
    initializeAuth().finally(() => {
      clearTimeout(timeout);
    });
    
    return () => clearTimeout(timeout);
  }, [accounts, instance]);

  // Background polling for GPU metrics - runs regardless of active section
  useEffect(() => {
    if (!currentUser) return; // Only start polling when user is authenticated
    
    // Load GPU metrics immediately
    loadGPUMetrics();
    
    // Set up interval to refresh every 30 seconds
    const gpuInterval = setInterval(() => {
      loadGPUMetrics();
    }, 30000);
    
    return () => clearInterval(gpuInterval);
  }, [currentUser]); // Only re-run if currentUser changes

  // Load user management data once on authentication
  useEffect(() => {
    if (!currentUser) return;
    
    // Load user management data immediately
    loadUserManagementData();
  }, [currentUser]);

  // Save GPU metrics cache to localStorage whenever it updates
  useEffect(() => {
    if (gpuMetricsCache.lastUpdated) {
      try {
        localStorage.setItem('gpuMetricsCache', JSON.stringify(gpuMetricsCache));
      } catch (e) {
        console.error('Error saving GPU metrics cache:', e);
      }
    }
  }, [gpuMetricsCache]);

  // Save user management cache to localStorage whenever it updates
  useEffect(() => {
    if (userManagementCache.lastUpdated) {
      try {
        localStorage.setItem('userManagementCache', JSON.stringify(userManagementCache));
      } catch (e) {
        console.error('Error saving user management cache:', e);
      }
    }
  }, [userManagementCache]);

  // Save Azure users cache to localStorage whenever it updates
  useEffect(() => {
    if (azureUsersCache.lastUpdated) {
      try {
        localStorage.setItem('azureUsersCache', JSON.stringify(azureUsersCache));
      } catch (e) {
        console.error('Error saving Azure users cache:', e);
      }
    }
  }, [azureUsersCache]);

  // Load Azure users once on authentication for GPU settings
  useEffect(() => {
    if (!currentUser) return;
    
    // Load Azure users immediately if not already loaded
    if (azureUsersCache.users.length === 0 && !azureUsersCache.isLoading) {
      loadAzureUsers();
    }
  }, [currentUser]);

  const loadAzureUsers = async () => {
    try {
      setAzureUsersCache(prev => ({ ...prev, isLoading: true }));
      const response = await getAllAzureUsers();
      setAzureUsersCache({
        users: response.data.users || [],
        lastUpdated: new Date(),
        isLoading: false
      });
    } catch (error) {
      console.error('Error loading Azure users:', error);
      setAzureUsersCache(prev => ({ ...prev, isLoading: false }));
    }
  };

  const fetchCurrentUser = async () => {
    try {
      // Use api service which automatically handles authentication
      const response = await api.get('/api/users/me');
      setCurrentUser(response.data);
      // Cache user data in localStorage for immediate availability on refresh
      if (response.data) {
        localStorage.setItem('currentUser', JSON.stringify(response.data));
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      // If user is not authenticated or there's an error, show login
      if (error.response?.status === 401 || error.response?.status === 403) {
        console.log('User not authenticated or authorized');
      }
    } finally {
      setAuthLoading(false);
    }
  };

  const handleWebSocketMessage = (message) => {
    if (message.type === 'health_update') {
      // Update health status in cache
      setHealthcheckCache(prev => {
        const healthStatuses = [...prev.healthStatuses];
        const index = healthStatuses.findIndex(h => h.url_id === message.data.url_id);
        if (index >= 0) {
          healthStatuses[index] = {
            url_id: message.data.url_id,
            status: message.data.status,
            response_time: message.data.response_time,
            status_code: message.data.status_code,
            checked_at: message.data.checked_at,
            error_message: message.data.error_message
          };
        } else {
          healthStatuses.push({
            url_id: message.data.url_id,
            status: message.data.status,
            response_time: message.data.response_time,
            status_code: message.data.status_code,
            checked_at: message.data.checked_at,
            error_message: message.data.error_message
          });
        }
        return {
          ...prev,
          healthStatuses,
          lastUpdated: new Date()
        };
      });
    }
  };

  const loadUrls = async () => {
    try {
      setHealthcheckCache(prev => ({ ...prev, isLoading: true }));
      const response = await getAllUrls();
      setHealthcheckCache(prev => ({
        ...prev,
        urls: response.data,
        lastUpdated: new Date(),
        isLoading: false
      }));
    } catch (error) {
      console.error('Error loading URLs:', error);
      setHealthcheckCache(prev => ({ ...prev, isLoading: false }));
    }
  };

  const loadHealthStatuses = async () => {
    try {
      const response = await getAllLatestHealth();
      setHealthcheckCache(prev => ({
        ...prev,
        healthStatuses: response.data,
        lastUpdated: new Date()
      }));
    } catch (error) {
      console.error('Error loading health statuses:', error);
    }
  };

  const loadServers = async () => {
    try {
      const response = await getAllServers();
      setHealthcheckCache(prev => ({
        ...prev,
        servers: response.data,
        lastUpdated: new Date()
      }));
    } catch (error) {
      console.error('Error loading servers:', error);
    }
  };

  const loadGPUMetrics = async () => {
    try {
      setGpuMetricsCache(prev => ({ ...prev, isLoading: true }));
      const response = await getOverallGPUMetrics();
      
      setGpuMetricsCache({
        overall: response.data.overall || [],
        individual: response.data.individual || [],
        lastUpdated: new Date(),
        isLoading: false
      });
    } catch (error) {
      console.error('Error loading GPU metrics:', error);
      setGpuMetricsCache(prev => ({ ...prev, isLoading: false }));
    }
  };

  const loadUserManagementData = async (fullReload = true) => {
    try {
      setUserManagementCache(prev => ({ ...prev, isLoading: true }));
      
      if (fullReload) {
        // Load all user management data in parallel (full reload)
        const [azureUsersRes, dbUsersRes, rolesRes] = await Promise.all([
          getAllAzureUsers().catch(err => {
            console.error('Error loading Azure users:', err);
            return { data: { users: [] } };
          }),
          api.get('/api/users/').catch(err => {
            console.error('Error loading DB users:', err);
            return { data: [] };
          }),
          api.get('/api/users/roles').catch(err => {
            console.error('Error loading roles:', err);
            // Fallback roles
            return {
              data: [
                { role_name: 'admin', display_name: 'Administrator' },
                { role_name: 'owner', display_name: 'Owner' },
                { role_name: 'editor', display_name: 'Editor' },
                { role_name: 'viewer', display_name: 'Viewer' }
              ]
            };
          })
        ]);
        
        setUserManagementCache({
          azureUsers: azureUsersRes.data.users || [],
          dbUsers: dbUsersRes.data || [],
          roles: rolesRes.data || [],
          lastUpdated: new Date(),
          isLoading: false
        });
      } else {
        // Only reload DB users (much faster for role updates)
        const dbUsersRes = await api.get('/api/users/').catch(err => {
          console.error('Error loading DB users:', err);
          return { data: [] };
        });
        
        setUserManagementCache(prev => ({
          ...prev,
          dbUsers: dbUsersRes.data || [],
          lastUpdated: new Date(),
          isLoading: false
        }));
      }
    } catch (error) {
      console.error('Error loading user management data:', error);
      setUserManagementCache(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleSectionChange = (section) => {
    setActiveSection(section);
    localStorage.setItem('activeSection', section);
  };

  const handleEnvironmentChange = (environment) => {
    setActiveEnvironment(environment);
    localStorage.setItem('activeEnvironment', environment);
    setActiveCategory(null); // Reset category when environment changes
  };

  const handleCategoryChange = (category) => {
    setActiveCategory(category);
  };

  const handleAddUrl = () => {
    setEditUrl(null);
    setIsModalOpen(true);
  };

  const handleEditUrl = (url) => {
    setEditUrl(url);
    setIsModalOpen(true);
  };

  const handleDeleteUrl = async (urlId) => {
    if (window.confirm('Are you sure you want to delete this URL?')) {
      try {
        await deleteUrlApi(urlId);
        await loadUrls();
        await loadHealthStatuses();
      } catch (error) {
        console.error('Error deleting URL:', error);
        alert('Failed to delete URL');
      }
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditUrl(null);
  };

  const handleModalSuccess = async () => {
    await loadUrls();
    await loadHealthStatuses();
  };

  const handleAddServer = () => {
    setEditServer(null);
    setIsServerModalOpen(true);
  };

  const handleEditServer = (server) => {
    setEditServer(server);
    setIsServerModalOpen(true);
  };

  const handleDeleteServer = async (serverId) => {
    if (window.confirm('Are you sure you want to delete this server?')) {
      try {
        await deleteServerApi(serverId);
        await loadServers();
      } catch (error) {
        console.error('Error deleting server:', error);
        alert('Failed to delete server');
      }
    }
  };

  const handleServerModalClose = () => {
    setIsServerModalOpen(false);
    setEditServer(null);
  };

  const handleServerModalSuccess = async () => {
    await loadServers();
  };

  const handleAddGPUServer = () => {
    setEditGPUServer(null);
    setIsGPUServerModalOpen(true);
  };

  const handleGPUServerModalClose = () => {
    setIsGPUServerModalOpen(false);
    setEditGPUServer(null);
  };

  const handleGPUServerModalSuccess = async () => {
    // Refresh can be added if needed
    setIsGPUServerModalOpen(false);
  };

  const getFilteredUrls = () => {
    let filtered = healthcheckCache.urls.filter(url => url.environment === activeEnvironment);
    if (activeCategory) {
      filtered = filtered.filter(url => url.project_category === activeCategory);
    }
    return filtered;
  };

  const getUrlsByEnvironment = () => {
    const result = {
      production: healthcheckCache.urls.filter(u => u.environment === 'production'),
      development: healthcheckCache.urls.filter(u => u.environment === 'development'),
      staging: healthcheckCache.urls.filter(u => u.environment === 'staging')
    };
    return result;
  };

  const getCategories = () => {
    const envUrls = healthcheckCache.urls.filter(u => u.environment === activeEnvironment);
    const categories = [...new Set(envUrls.map(url => url.project_category).filter(cat => cat))];
    return categories.sort();
  };

  const getPageTitle = () => {
    if (activeSection === 'server') {
      return 'Server Management';
    }
    if (activeSection === 'gpu-stats') {
      return 'GPU Statistics';
    }
    if (activeSection === 'user-management') {
      return 'User Management';
    }
    return activeEnvironment.charAt(0).toUpperCase() + activeEnvironment.slice(1);
  };

  if (authLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }

  // Show loading screen while MSAL is initializing
  if (authLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #0078d4',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }}></div>
          <p style={{ color: '#666', fontSize: '16px' }}>Verifying authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <UnauthenticatedTemplate>
        <Login />
      </UnauthenticatedTemplate>

      <AuthenticatedTemplate>
        <div className="app-container">
          <Sidebar
            currentUser={currentUser}
            activeSection={activeSection}
            onSectionChange={handleSectionChange}
            activeEnvironment={activeEnvironment}
            onEnvironmentChange={handleEnvironmentChange}
          />

          <main className="main-content">
        <TopBar
          title={getPageTitle()}
          onAddUrl={
            currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor')
              ? (activeSection === 'healthcheck' ? handleAddUrl : (activeSection === 'server' ? handleAddServer : (activeSection === 'gpu-stats' ? handleAddGPUServer : null)))
              : null
          }
          buttonText={activeSection === 'healthcheck' ? 'Add URL' : (activeSection === 'server' ? 'Add Server' : (activeSection === 'gpu-stats' ? 'Add Server' : undefined))}
        />

        {activeSection === 'healthcheck' && (
          <>
            <CategoryDropdown
              activeCategory={activeCategory}
              onCategoryChange={handleCategoryChange}
              categories={getCategories()}
            />

            <div className="content-area">
              {healthcheckCache.isLoading ? (
                <div className="loading-state">Loading...</div>
              ) : (
                <URLTable
                  urls={getFilteredUrls()}
                  healthStatuses={healthcheckCache.healthStatuses}
                  onEdit={currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor') ? handleEditUrl : null}
                  onDelete={currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor') ? handleDeleteUrl : null}
                  onRefresh={loadUrls}
                  servers={healthcheckCache.servers}
                  currentUserRole={currentUser?.user?.role}
                />
              )}
            </div>
          </>
        )}

        {activeSection === 'gpu-stats' && (
          <div className="content-area">
            <GPUStats
              currentUserRole={currentUser?.user?.role}
              cachedData={gpuMetricsCache}
              onRefresh={loadGPUMetrics}
              azureUsersCache={azureUsersCache}
            />
          </div>
        )}

        {activeSection === 'server' && (
          <div className="content-area">
            <ServerTable
              servers={healthcheckCache.servers}
              onEdit={currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor') ? handleEditServer : null}
              onDelete={currentUser && currentUser.user && (currentUser.user.role === 'admin' || currentUser.user.role === 'owner' || currentUser.user.role === 'editor') ? handleDeleteServer : null}
              currentUserRole={currentUser?.user?.role}
            />
          </div>
        )}

        {activeSection === 'user-management' && (
          <div className="content-area-full">
            <UserManagement 
              currentUser={currentUser}
              cachedData={userManagementCache}
              onRefresh={loadUserManagementData}
            />
          </div>
        )}
      </main>

      <AddURLModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
        editUrl={editUrl}
        servers={healthcheckCache.servers}
      />

      <AddServerModal
        isOpen={isServerModalOpen}
        onClose={handleServerModalClose}
        onSuccess={handleServerModalSuccess}
        editServer={editServer}
      />

      <AddGPUServerModal
        isOpen={isGPUServerModalOpen}
        onClose={handleGPUServerModalClose}
        onSuccess={handleGPUServerModalSuccess}
        editServer={editGPUServer}
      />
        </div>
      </AuthenticatedTemplate>
    </>
  );
}

export default App;