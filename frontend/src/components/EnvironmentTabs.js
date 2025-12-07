import React from 'react';
import '../styles/components/TopBar.css';

const EnvironmentTabs = ({ activeEnvironment, activeCategory, onEnvironmentChange, onCategoryChange, urlsByEnvironment }) => {
  const environments = [
    { name: 'Production', value: 'production' },
    { name: 'Development', value: 'development' },
    { name: 'Staging', value: 'staging' }
  ];

  // Get project categories for the active environment
  const getProjectCategories = () => {
    const urls = urlsByEnvironment[activeEnvironment] || [];
    const categories = [...new Set(urls.map(url => url.project_category).filter(cat => cat))];
    return categories.sort();
  };

  const projectCategories = getProjectCategories();

  return (
    <div className="tabs-container">
      <div className="tabs">
        {environments.map((env) => (
          <div
            key={env.value}
            className={`tab ${activeEnvironment === env.value ? 'active' : ''}`}
            onClick={() => onEnvironmentChange(env.value)}
          >
            {env.name}
          </div>
        ))}
      </div>
      
      {projectCategories.length > 0 && (
        <div className="category-tabs">
          {projectCategories.map((category) => (
            <div
              key={category}
              className={`category-tab ${activeCategory === category ? 'active' : ''}`}
              onClick={() => onCategoryChange(activeCategory === category ? null : category)}
            >
              {category}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EnvironmentTabs;