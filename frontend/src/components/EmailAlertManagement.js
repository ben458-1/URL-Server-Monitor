import React, { useState, useEffect } from 'react';
import CategoryDropdown from './CategoryDropdown';
import '../styles/components/EmailAlertManagement.css';

const EmailAlertManagement = ({ urls }) => {
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [categories, setCategories] = useState([]);
  const [filteredUrls, setFilteredUrls] = useState([]);

  useEffect(() => {
    // Extract unique categories from URLs
    const uniqueCategories = [...new Set(urls.map(url => url.project_category).filter(cat => cat))];
    const sortedCategories = uniqueCategories.sort();
    setCategories(sortedCategories);
    
    // Set first category as default if available and no category is selected
    if (sortedCategories.length > 0 && !selectedCategory) {
      setSelectedCategory(sortedCategories[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urls]);

  useEffect(() => {
    if (selectedCategory) {
      const filtered = urls.filter(url => url.project_category === selectedCategory);
      console.log('📋 Filtered URLs for category', selectedCategory, ':', filtered);
      console.log('📋 URLs with alert_emails:', filtered.filter(u => u.alert_emails && u.alert_emails.length > 0));
      setFilteredUrls(filtered);
    } else {
      setFilteredUrls([]);
    }
  }, [selectedCategory, urls]);

  const handleAddWhatsApp = () => {
    alert('WhatsApp functionality - To be implemented in future');
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
  };

  return (
    <div className="email-alert-page">
      <CategoryDropdown
        activeCategory={selectedCategory}
        onCategoryChange={handleCategoryChange}
        categories={categories}
        hideAllOption={true}
      />

      <div className="email-alert-content">
        {!selectedCategory || filteredUrls.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"></div>
            <div className="empty-title">No URLs Found</div>
            <div className="empty-text">
              {selectedCategory
                ? `No URLs in the "${selectedCategory}" category`
                : 'Select a category to view URLs and manage email alerts.'}
            </div>
          </div>
        ) : (
          <div className="table-container">
            <div className="table-header">
              <h3 className="table-title">WISE - Email Alert Configuration</h3>
              <div className="table-actions">
                <button className="header-action-btn whatsapp-btn" onClick={() => handleAddWhatsApp()}>
                  + Add WhatsApp
                </button>
              </div>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>URL</th>
                  <th>Environment</th>
                  <th>Email Alerts</th>
                  <th>WhatsApp Alerts</th>
                </tr>
              </thead>
              <tbody>
                {filteredUrls.map((url) => (
                  <tr key={url.id}>
                    <td>{url.project_name}</td>
                    <td>
                      <a href={url.url} target="_blank" rel="noopener noreferrer" className="url-link">
                        {url.url}
                      </a>
                    </td>
                    <td>
                      <span className={`env-badge ${url.environment}`}>
                        {url.environment}
                      </span>
                    </td>
                    <td>
                      <span className={`alert-count ${url.alert_emails && url.alert_emails.length > 0 ? 'has-alerts' : 'no-alerts'}`}>
                        {url.alert_emails && url.alert_emails.length > 0 
                          ? `${url.alert_emails.length} configured` 
                          : '0 configured'}
                      </span>
                    </td>
                    <td>
                      <span className="alert-count no-alerts">0 configured</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};

export default EmailAlertManagement;