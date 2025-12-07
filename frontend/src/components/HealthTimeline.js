import React, { useState, useEffect, useRef } from 'react';
import { getHealthHistory } from '../services/api';
import '../styles/components/StatusBadge.css';

// Global cache for health history to avoid reloading
const healthHistoryCache = new Map();
const CACHE_DURATION = 30000; // 30 seconds

const HealthTimeline = ({ urlId }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    loadHistory();
    
    // Refresh every 30 seconds
    const interval = setInterval(loadHistory, 30000);
    
    return () => {
      isMounted.current = false;
      clearInterval(interval);
    };
  }, [urlId]);

  const loadHistory = async () => {
    try {
      // Check cache first
      const cached = healthHistoryCache.get(urlId);
      const now = Date.now();
      
      if (cached && (now - cached.timestamp) < CACHE_DURATION) {
        if (isMounted.current) {
          setHistory(cached.data);
          setLoading(false);
        }
        return;
      }
      
      // Only show loading if we don't have cached data
      if (!cached && isMounted.current) {
        setLoading(true);
      }
      
      const response = await getHealthHistory(urlId, 10);
      
      if (isMounted.current) {
        setHistory(response.data);
        setLoading(false);
        
        // Update cache
        healthHistoryCache.set(urlId, {
          data: response.data,
          timestamp: now
        });
      }
    } catch (error) {
      console.error('Error loading health history:', error);
      if (isMounted.current) {
        setLoading(false);
      }
    }
  };

  if (loading) {
    return <span className="health-timeline-loading">Loading...</span>;
  }

  if (history.length === 0) {
    return <span className="health-timeline-empty">No data</span>;
  }

  const onlineCount = history.filter(h => h.status === 'online').length;
  const totalCount = history.length;
  const uptimePercentage = totalCount > 0 ? Math.round((onlineCount / totalCount) * 100) : 0;

  return (
    <div className="health-timeline">
      <div className="timeline-dots">
        {history.slice(0, 10).reverse().map((check, index) => (
          <span
            key={index}
            className={`timeline-dot ${check.status}`}
            title={`${check.status} - ${new Date(check.checked_at).toLocaleString()}`}
          ></span>
        ))}
      </div>
      <div className="timeline-stats">
        {uptimePercentage}% uptime ({onlineCount}/{totalCount})
      </div>
    </div>
  );
};

export default HealthTimeline;