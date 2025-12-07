import React, { useState, useEffect, useRef } from 'react';
import '../styles/components/CategoryDropdown.css';

const CategoryDropdown = ({ activeCategory, onCategoryChange, categories, hideAllOption = false }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [sortBy, setSortBy] = useState('name'); // 'name' or 'date'
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);
  const sortRef = useRef(null);

  const handleCategorySelect = (category) => {
    onCategoryChange(category);
    setShowDropdown(false);
    setSearchTerm('');
    setShowSearch(false);
  };

  const toggleSearch = () => {
    const willShowSearch = !showSearch;
    setShowSearch(willShowSearch);
    setSearchTerm('');
    if (willShowSearch) {
      // Delay focus to allow animation to start
      setTimeout(() => searchInputRef.current?.focus(), 200);
    }
  };

  const handleSortSelect = (option) => {
    setSortBy(option);
    setShowSortMenu(false);
  };

  const filteredCategories = categories.filter(category =>
    category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort categories based on selected option
  const sortedCategories = [...filteredCategories].sort((a, b) => {
    if (sortBy === 'name') {
      return a.localeCompare(b);
    }
    // For date sorting, you might need to pass date info from parent
    // For now, we'll just use name as fallback
    return a.localeCompare(b);
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    // Close dropdown on Escape key
    const handleEscKey = (event) => {
      if (event.key === 'Escape') {
        if (showDropdown) setShowDropdown(false);
        if (showSortMenu) setShowSortMenu(false);
      }
    };

    if (showDropdown || showSortMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscKey);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [showDropdown, showSortMenu]);

  // Close sort menu when clicking outside
  useEffect(() => {
    const handleClickOutsideSort = (event) => {
      if (sortRef.current && !sortRef.current.contains(event.target)) {
        setShowSortMenu(false);
      }
    };

    if (showSortMenu) {
      document.addEventListener('mousedown', handleClickOutsideSort);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutsideSort);
    };
  }, [showSortMenu]);

  if (!categories || categories.length === 0) {
    return null;
  }

  const displayValue = activeCategory || (hideAllOption ? 'Select Category' : 'All Categories');

  return (
    <div className="category-dropdown-container" ref={dropdownRef}>
      <div className="category-dropdown-wrapper">
        <label className="category-dropdown-label">Filter by Category</label>
        <div className="category-dropdown-controls">
          {showSearch ? (
            <div className="category-search-input-wrapper">
              <svg
                className="category-search-icon"
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
                ref={searchInputRef}
                type="text"
                className="category-search-input"
                placeholder="Search categories..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') {
                    setShowSearch(false);
                    setSearchTerm('');
                  }
                }}
              />
              <button
                className="category-search-close"
                onClick={toggleSearch}
                aria-label="Close search"
              >
                ✕
              </button>
            </div>
          ) : (
            <>
              <div
                className={`category-dropdown-trigger ${showDropdown ? 'open' : ''}`}
                onClick={() => setShowDropdown(!showDropdown)}
                role="button"
                aria-haspopup="listbox"
                aria-expanded={showDropdown}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setShowDropdown(!showDropdown);
                  }
                }}
              >
                <span className="category-dropdown-value">{displayValue}</span>
                <svg
                  className={`category-dropdown-icon ${showDropdown ? 'rotate' : ''}`}
                  width="18"
                  height="18"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M4 6L8 10L12 6"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <button
                className="category-search-button"
                onClick={toggleSearch}
                aria-label="Search categories"
                title="Search categories"
              >
                <svg
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
              </button>
              <div className="category-sort-container" ref={sortRef}>
                <button
                  className={`category-sort-button ${showSortMenu ? 'active' : ''}`}
                  onClick={() => setShowSortMenu(!showSortMenu)}
                  aria-label="Sort categories"
                  title="Sort categories"
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M3 4.5H21M3 9H12M3 13.5H12M17 13.5L17 20M17 20L14 17M17 20L20 17"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                
                {showSortMenu && (
                  <div className="category-sort-menu">
                    <div className="category-sort-header">Sort by</div>
                    <div
                      className={`category-sort-option ${sortBy === 'name' ? 'active' : ''}`}
                      onClick={() => handleSortSelect('name')}
                    >
                      <span className="category-sort-icon"></span>
                      <span className="category-sort-text">Name (A-Z)</span>
                      {sortBy === 'name' && <span className="category-sort-check">✓</span>}
                    </div>
                    <div
                      className={`category-sort-option ${sortBy === 'date' ? 'active' : ''}`}
                      onClick={() => handleSortSelect('date')}
                    >
                      <span className="category-sort-icon"></span>
                      <span className="category-sort-text">Date Added</span>
                      {sortBy === 'date' && <span className="category-sort-check">✓</span>}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      
      {(showDropdown || (showSearch && searchTerm)) && (
        <div className="category-dropdown-menu" role="listbox">
          <div className="category-dropdown-menu-items">
            {!showSearch && !hideAllOption && (
              <>
                <div
                  className={`category-dropdown-item ${!activeCategory ? 'active' : ''}`}
                  onClick={() => handleCategorySelect(null)}
                  role="option"
                  aria-selected={!activeCategory}
                >
                  <span className="category-item-text">
                    <span className="category-item-icon"></span>
                    All Categories
                  </span>
                  {!activeCategory && <span className="category-item-check">✓</span>}
                </div>
                
                {categories.length > 0 && <div className="category-dropdown-divider" />}
              </>
            )}
            
            {(showSearch ? sortedCategories : categories).map((category) => (
              <div
                key={category}
                className={`category-dropdown-item ${activeCategory === category ? 'active' : ''}`}
                onClick={() => handleCategorySelect(category)}
                role="option"
                aria-selected={activeCategory === category}
              >
                <span className="category-item-text">
                  <span className="category-item-icon"></span>
                  {category}
                </span>
                {activeCategory === category && <span className="category-item-check">✓</span>}
              </div>
            ))}
            
            {showSearch && sortedCategories.length === 0 && (
              <div className="category-dropdown-empty">
                <div className="category-dropdown-empty-icon">🔍</div>
                No categories found matching "{searchTerm}"
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryDropdown;