import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import '../styles/components/UserManagement.css';

function UserManagement({ currentUser: propCurrentUser, cachedData, onRefresh }) {
  const [currentUser, setCurrentUser] = useState(propCurrentUser);
  
  // Use cached data from props
  const azureUsers = cachedData?.azureUsers || [];
  const dbUsers = cachedData?.dbUsers || [];
  const roles = cachedData?.roles || [];
  const loading = cachedData?.isLoading && azureUsers.length === 0; // Only show loading if no cached data
  
  // Search states
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const searchInputRef = useRef(null);
  
  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [usersPerPage] = useState(15);
  
  // Confirmation modal states
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingRoleChange, setPendingRoleChange] = useState(null);

  useEffect(() => {
    setCurrentUser(propCurrentUser);
  }, [propCurrentUser]);

  // Log when using cached data
  useEffect(() => {
    if (azureUsers.length > 0 && cachedData?.lastUpdated) {
      console.log('👥 Using cached user management data. Last updated:', cachedData.lastUpdated.toLocaleTimeString());
    }
  }, [cachedData]);

  useEffect(() => {
    if (showSearch && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 200);
    }
  }, [showSearch]);

  const handleRoleChangeClick = (email, newRole, oldRole, azureUserId, userName, isNewUser) => {
    setPendingRoleChange({ email, newRole, oldRole, azureUserId, userName, isNewUser });
    setShowConfirmModal(true);
  };

  const handleConfirmRoleChange = async () => {
    if (!pendingRoleChange) return;
    
    const { email, newRole, azureUserId, userName, isNewUser } = pendingRoleChange;
    setShowConfirmModal(false);
    
    try {
      // RULE: If changing to 'viewer', remove from DB (viewer is default)
      // RULE: If changing to admin/owner/editor, store in DB
      
      if (newRole === 'viewer') {
        // Remove from DB if they exist (viewer is default, no DB entry needed)
        if (!isNewUser) {
          console.log('Removing user from DB (setting to default viewer):', email);
          
          try {
            await api.delete(`/api/users/${encodeURIComponent(email)}`);
            console.log('Delete successful');
            if (onRefresh) await onRefresh(false); // Fast refresh - only DB users
            alert('User set to default viewer role (removed from database)');
          } catch (error) {
            console.error('Delete failed:', error);
            const errorMessage = error.response?.data?.detail || 'Failed to update role';
            alert(errorMessage);
          }
        } else {
          // User doesn't exist in DB and staying as viewer - nothing to do
          alert('User already has default viewer role');
        }
      } else {
        // Elevated role (admin, owner, editor) - store in DB
        if (isNewUser) {
          // Create new user with elevated role
          console.log('Creating user with elevated role:', { email, userName, azureUserId, newRole });
          
          try {
            await api.post('/api/users/', { 
              email: email,
              name: userName,
              azure_user_id: azureUserId,
              role: newRole 
            });
            console.log('Create successful');
            if (onRefresh) await onRefresh(false); // Fast refresh - only DB users
            alert('User role assigned successfully');
          } catch (error) {
            console.error('Create failed:', error);
            const errorMessage = error.response?.data?.detail || 'Failed to assign role';
            alert(errorMessage);
          }
        } else {
          // Update existing user's elevated role
          console.log('Updating user role:', { email, newRole });
          
          try {
            await api.put(`/api/users/${encodeURIComponent(email)}/role`, { role: newRole });
            console.log('Update successful');
            if (onRefresh) await onRefresh(false); // Fast refresh - only DB users
            alert('User role updated successfully');
          } catch (error) {
            console.error('Update failed:', error);
            const errorMessage = error.response?.data?.detail || 'Failed to update role';
            alert(errorMessage);
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to update role');
    } finally {
      setPendingRoleChange(null);
    }
  };

  const handleCancelRoleChange = () => {
    setShowConfirmModal(false);
    setPendingRoleChange(null);
  };

  const handleToggleStatus = async (email, currentStatus) => {
    const action = currentStatus ? 'disable' : 'enable';
    if (!window.confirm(`Are you sure you want to ${action} this user?`)) return;
    
    try {
      await api.put(`/api/users/${encodeURIComponent(email)}/status`, { is_active: !currentStatus });
      if (onRefresh) await onRefresh(false); // Fast refresh - only DB users
      alert(`User ${action}d successfully`);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = error.response?.data?.detail || `Failed to ${action} user`;
      alert(errorMessage);
    }
  };

  const toggleSearch = () => {
    const willShowSearch = !showSearch;
    setShowSearch(willShowSearch);
    setSearchTerm('');
  };

  const getUserPermissions = (user) => {
    const role = roles.find(r => r.role_name === user.role);
    if (!role) return [];
    
    const permissions = [];
    if (role.can_manage_users) permissions.push('Manage Users');
    if (role.can_add_urls) permissions.push('Add URLs');
    if (role.can_edit_urls) permissions.push('Edit URLs');
    if (role.can_delete_urls) permissions.push('Delete URLs');
    if (role.can_add_servers) permissions.push('Add Servers');
    if (role.can_edit_servers) permissions.push('Edit Servers');
    if (role.can_delete_servers) permissions.push('Delete Servers');
    if (role.can_manage_email_alerts) permissions.push('Manage Alerts');
    
    return permissions;
  };

  const getDbUserByEmail = (email) => {
    return dbUsers.find(u => u.email === email);
  };

  // Filter functions
  const filterUsers = (users, isDbUsers = false) => {
    if (!searchTerm) return users;
    const term = searchTerm.toLowerCase();
    return users.filter(user => {
      const name = isDbUsers ? (user.name || '') : (user.displayName || '');
      const email = user.email || '';
      return name.toLowerCase().includes(term) || email.toLowerCase().includes(term);
    });
  };

  // Pagination functions
  const getPaginatedUsers = (users) => {
    const indexOfLastUser = currentPage * usersPerPage;
    const indexOfFirstUser = indexOfLastUser - usersPerPage;
    return users.slice(indexOfFirstUser, indexOfLastUser);
  };

  const getTotalPages = (users) => {
    return Math.ceil(users.length / usersPerPage);
  };

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getPageNumbers = (totalPages) => {
    const pages = [];
    const maxVisible = 5;
    
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      if (currentPage <= 3) {
        for (let i = 1; i <= 4; i++) pages.push(i);
        pages.push('...');
        pages.push(totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1);
        pages.push('...');
        for (let i = totalPages - 3; i <= totalPages; i++) pages.push(i);
      } else {
        pages.push(1);
        pages.push('...');
        for (let i = currentPage - 1; i <= currentPage + 1; i++) pages.push(i);
        pages.push('...');
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  if (loading) {
    return <div className="user-management-loading">Loading...</div>;
  }

  return (
    <div className="user-management">
      {/* Search Bar - Compact version */}
      <div className="user-search-bar">
        <div className="user-search-input-container">
          <svg
            className="user-search-input-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M21 21L15 15M17 10C17 13.866 13.866 17 10 17C6.13401 17 3 13.866 3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <input
            type="text"
            className="user-search-input-field"
            placeholder="Search user"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
          />
          {searchTerm && (
            <button
              className="user-search-clear"
              onClick={() => {
                setSearchTerm('');
                setCurrentPage(1);
              }}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Users Table */}
      {(() => {
        const filteredUsers = filterUsers(azureUsers);
        const paginatedUsers = getPaginatedUsers(filteredUsers);
        const totalPages = getTotalPages(filteredUsers);
        
        return (
          <>
            <div className="users-table-container">
              <table className="users-table users-table--two-column">
                <colgroup>
                  <col className="users-col-email" />
                  <col className="users-col-role" />
                </colgroup>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th className="users-header-role">{(currentUser?.user?.role === 'admin' || currentUser?.user?.role === 'owner') ? 'Edit Role' : 'Role'}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedUsers.map(azureUser => {
                    const dbUser = getDbUserByEmail(azureUser.email);
                    const currentUserRole = currentUser?.user?.role;
                    const isAdministrator = currentUserRole === 'admin';
                    const isOwner = currentUserRole === 'owner';
                    const canEdit = isAdministrator || isOwner;
                    
                    // Determine if this specific user can be edited
                    let canEditThisUser = false;
                    if (isAdministrator) {
                      canEditThisUser = true; // Admin can edit everyone
                    } else if (isOwner) {
                      // Owner can edit everyone except admins and owners
                      canEditThisUser = (!dbUser || (dbUser.role !== 'admin' && dbUser.role !== 'owner'));
                    }
                    
                    // DEFAULT ROLE: Everyone defaults to 'viewer' permission (read-only)
                    const userRole = dbUser?.role || 'viewer';
                    
                    // Debug log
                    if (azureUser.email && roles.length > 0) {
                      console.log(`User: ${azureUser.email}, Role: ${userRole}, Roles available:`, roles);
                    }
                    
                    return (
                      <tr key={azureUser.id}>
                        <td className="users-cell-email">{azureUser.email}</td>
                        <td className="users-cell-role">
                          {canEditThisUser ? (
                            <select
                              value={userRole}
                              onChange={(e) => handleRoleChangeClick(
                                azureUser.email,
                                e.target.value, 
                                userRole,
                                azureUser.id,
                                azureUser.displayName,
                                !dbUser // isNewUser - true if dbUser doesn't exist
                              )}
                              className="role-select-dropdown"
                              title={`Current role: ${roles.find(r => r.role_name === userRole)?.display_name || userRole}`}
                            >
                              {roles.length > 0 ? (
                                roles
                                  .filter(role => {
                                    // Always include the current role
                                    if (role.role_name === userRole) return true;
                                    // Administrators can assign all 4 roles: admin, owner, editor, viewer
                                    if (isAdministrator) return true;
                                    // Owners can only assign editor and viewer roles
                                    if (isOwner) return role.role_name === 'editor' || role.role_name === 'viewer';
                                    return false;
                                  })
                                  .sort((a, b) => {
                                    // Sort roles in order: admin, owner, editor, viewer
                                    const order = { 'admin': 1, 'owner': 2, 'editor': 3, 'viewer': 4 };
                                    return order[a.role_name] - order[b.role_name];
                                  })
                                  .map(role => (
                                    <option key={role.role_name} value={role.role_name}>
                                      {role.display_name || role.role_name}
                                    </option>
                                  ))
                              ) : (
                                <>
                                  <option value="viewer">Viewer</option>
                                  <option value="editor">Editor</option>
                                  <option value="owner">Owner</option>
                                  <option value="admin">Administrator</option>
                                </>
                              )}
                            </select>
                          ) : (
                            <span className="role-badge">{roles.find(r => r.role_name === userRole)?.display_name || userRole}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredUsers.length === 0 && (
                <div className="no-users">
                  {searchTerm ? `No users found matching "${searchTerm}"` : 'No users found'}
                </div>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination-container">
                <button
                  className="pagination-button"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Previous
                </button>

                <div className="pagination-numbers">
                  {getPageNumbers(totalPages).map((page, index) => (
                    page === '...' ? (
                      <span key={`ellipsis-${index}`} className="pagination-ellipsis">...</span>
                    ) : (
                      <button
                        key={page}
                        className={`pagination-number ${currentPage === page ? 'active' : ''}`}
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </button>
                    )
                  ))}
                </div>

                <button
                  className="pagination-button"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            )}
          </>
        );
      })()}

      {/* Confirmation Modal */}
      {showConfirmModal && pendingRoleChange && (
        <div className="role-modal-overlay" onClick={handleCancelRoleChange}>
          <div className="role-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="role-modal-header">
              <h3>Confirm Role Change</h3>
            </div>
            <div className="role-modal-body">
              <p className="role-modal-email">{pendingRoleChange.userEmail}</p>
              <div className="role-modal-change">
                <span className="role-modal-old">{roles.find(r => r.role_name === pendingRoleChange.oldRole)?.display_name || pendingRoleChange.oldRole}</span>
                <span className="role-modal-arrow">→</span>
                <span className="role-modal-new">{roles.find(r => r.role_name === pendingRoleChange.newRole)?.display_name || pendingRoleChange.newRole}</span>
              </div>
              <p className="role-modal-question">Are you sure you want to change this user's role?</p>
            </div>
            <div className="role-modal-footer">
              <button className="role-modal-btn role-modal-btn-cancel" onClick={handleCancelRoleChange}>
                Cancel
              </button>
              <button className="role-modal-btn role-modal-btn-confirm" onClick={handleConfirmRoleChange}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserManagement;
