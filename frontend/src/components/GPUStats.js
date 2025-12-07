import React, { useState, useEffect, useRef } from 'react';
import AddGPUServerModal from './AddGPUServerModal';
import ManageGPUModal from './ManageGPUModal';
import GaugeChart from './GaugeChart';
import '../styles/components/GPUStats.css';

function GPUStats({ currentUserRole, cachedData, onRefresh, azureUsersCache }) {
  const [expandedGPUs, setExpandedGPUs] = useState({}); // Format: { gpuName: true/false }
  const [animationKey, setAnimationKey] = useState(0); // For triggering re-animation
  const [manageModalOpen, setManageModalOpen] = useState(false);
  const [selectedGPUName, setSelectedGPUName] = useState(null);
  const editButtonRefs = useRef({}); // Store refs for each GPU's edit button
  const canEdit = currentUserRole === 'admin' || currentUserRole === 'owner' || currentUserRole === 'editor';

  // Use cached data from props - show cached data immediately, only show loading if absolutely no data
  const gpuMetrics = cachedData?.individual || [];
  const overallMetrics = cachedData?.overall || [];
  const hasData = gpuMetrics.length > 0;
  const loading = !hasData && cachedData?.isLoading;
  const error = null; // Error handling can be added to cachedData if needed

  // Log when using cached data
  useEffect(() => {
    if (gpuMetrics.length > 0 && cachedData?.lastUpdated) {
      console.log('📊 Using cached GPU metrics. Last updated:', cachedData.lastUpdated.toLocaleTimeString());
    }
  }, [cachedData]);

  const formatBytes = (mib) => {
    if (mib >= 1024) {
      return `${(mib / 1024).toFixed(1)} GiB`;
    }
    return `${mib} MiB`;
  };

  const formatDiskBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${bytes} B`;
  };

  const getUsagePercentage = (used, total) => {
    return ((used / total) * 100).toFixed(1);
  };

  const getProgressColor = (percentage) => {
    const percent = parseFloat(percentage);
    if (percent <= 50) {
      return '#22c55e'; // Vibrant Green
    } else if (percent <= 70) {
      return '#84cc16'; // Lime Green
    } else if (percent <= 85) {
      return '#eab308'; // Yellow
    } else if (percent <= 95) {
      return '#f97316'; // Orange
    } else {
      return '#ef4444'; // Red
    }
  };

  // Group metrics by GPU name
  const groupedMetrics = gpuMetrics.reduce((acc, metric) => {
    if (!acc[metric.gpu_name]) {
      acc[metric.gpu_name] = [];
    }
    acc[metric.gpu_name].push(metric);
    return acc;
  }, {});

  // Create a map of overall metrics by GPU name for easy lookup
  const overallMetricsMap = overallMetrics.reduce((acc, metric) => {
    acc[metric.gpu_name] = metric;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="loading-state">
        Loading GPU metrics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-state">
        {error}
      </div>
    );
  }

  if (gpuMetrics.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-title">No GPU Metrics Available</div>
        <div className="empty-text">No GPU metrics data found in the database</div>
      </div>
    );
  }

  const toggleGPUExpansion = (gpuName) => {
    setExpandedGPUs({
      ...expandedGPUs,
      [gpuName]: !expandedGPUs[gpuName]
    });
  };

  const handleManageGPU = (gpuName, e) => {
    e.stopPropagation(); // Prevent triggering the expand/collapse
    setSelectedGPUName(gpuName);
    setManageModalOpen(true);
  };

  const handleManageClose = () => {
    setManageModalOpen(false);
    setSelectedGPUName(null);
  };

  const handleManageUpdate = () => {
    // Reload metrics after settings update
    if (onRefresh) {
      onRefresh();
    }
  };

  return (
    <div className="gpu-stats-container" key={animationKey}>
      {Object.keys(groupedMetrics).map(gpuName => {
        const gpuGroup = groupedMetrics[gpuName];
        const overall = overallMetricsMap[gpuName];
        const isExpanded = expandedGPUs[gpuName];
        
        // If no overall metrics available, skip this group
        if (!overall) {
          return null;
        }
        
        return (
          <div key={gpuName} className="gpu-name-section">
            {/* GPU Name Header with Overall Gauges and Toggle */}
            <div className="gpu-name-header" onClick={() => toggleGPUExpansion(gpuName)}>
              <h2 className="gpu-name-title">{gpuName}</h2>
              
              {/* Overall Gauges */}
              <div className="overall-gauges">
                <div className="overall-gauge-card">
                  <GaugeChart 
                    value={overall.avg_gpu_utilization_pct || 0} 
                    max={100} 
                    size={70}
                    label="GPU"
                  />
                  <div className="overall-gauge-info">
                    <div className="overall-gauge-label">Avg GPU Utilization</div>
                    <div className="overall-gauge-value">{overall.avg_gpu_utilization_pct || 0}%</div>
                  </div>
                </div>
                
                <div className="overall-gauge-card">
                  <GaugeChart 
                    value={overall.gpu_memory_usage_pct || 0} 
                    max={100} 
                    size={70}
                    label="VRAM"
                  />
                  <div className="overall-gauge-info">
                    <div className="overall-gauge-label">Total GPU Memory</div>
                    <div className="overall-gauge-value">
                      {formatBytes(overall.total_gpu_memory_used_mib || 0)} / {formatBytes(overall.total_gpu_memory_total_mib || 0)}
                    </div>
                    <div className="overall-gauge-sub">
                      {formatBytes(overall.total_gpu_memory_free_mib || 0)} available
                    </div>
                  </div>
                </div>
                
                <div className="overall-gauge-card">
                  <GaugeChart 
                    value={overall.host_memory_usage_pct || 0} 
                    max={100} 
                    size={70}
                    label="RAM"
                  />
                  <div className="overall-gauge-info">
                    <div className="overall-gauge-label">Total Host RAM</div>
                    <div className="overall-gauge-value">
                      {formatBytes(overall.total_host_memory_used_mib || 0)} / {formatBytes(overall.max_host_memory_total_mib || 0)}
                    </div>
                    <div className="overall-gauge-sub">
                      {formatBytes((overall.max_host_memory_total_mib || 0) - (overall.total_host_memory_used_mib || 0))} available
                    </div>
                  </div>
                </div>
                
                <div className="overall-gauge-card">
                  <GaugeChart 
                    value={overall.host_disk_usage_pct || 0} 
                    max={100} 
                    size={70}
                    label="DISK"
                  />
                  <div className="overall-gauge-info">
                    <div className="overall-gauge-label">Host Disk</div>
                    <div className="overall-gauge-value">
                      {formatBytes(overall.host_disk_used_mib || 0)} / {formatBytes(overall.host_disk_total_mib || 0)}
                    </div>
                    <div className="overall-gauge-sub">
                      {formatBytes(overall.host_disk_free_mib || 0)} available
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Edit Button and Toggle Arrow */}
              <div className="header-actions">
                <div className="gpu-toggle-arrow">
                  <svg 
                    width="24" 
                    height="24" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2"
                    className={isExpanded ? 'arrow-expanded' : 'arrow-collapsed'}
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>
                
                {canEdit && (
                  <button
                    ref={(el) => (editButtonRefs.current[gpuName] = el)}
                    className="edit-gpu-button"
                    onClick={(e) => handleManageGPU(gpuName, e)}
                    title="Edit GPU Settings"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                  </button>
                )}
              </div>
            </div>
            
            {/* GPU Details - Show all GPUs when expanded */}
            <div className={`gpu-details-wrapper ${isExpanded ? 'expanded' : 'collapsed'}`}>
              <div className="gpu-details-list">
                {gpuGroup.map((metric) => {
                  const memUsagePercent = getUsagePercentage(metric.gpu_memory_used_mib, metric.gpu_memory_total_mib);
                  
                  return (
                    <div key={`${metric.host}-${metric.gpu_index}`} className="gpu-item">
                  <div className="gpu-header">
                    <div className="gpu-title-row">
                      <h3 className="gpu-title">GPU {metric.gpu_index}</h3>
                      <span className="gpu-host">{metric.host}</span>
                    </div>
                    <div className="gpu-timestamp">
                      {new Date(metric.timestamp).toLocaleTimeString()}
                    </div>
                  </div>

                  <div className="gpu-gauges-row">
                    <div className="gauge-card">
                      <GaugeChart 
                        value={metric.gpu_utilization_pct} 
                        max={100} 
                        size={85}
                        label="GPU"
                      />
                      <div className="gauge-info">
                        <div className="gauge-info-label">GPU Utilization</div>
                        <div className="gauge-info-value">{metric.gpu_utilization_pct}%</div>
                      </div>
                    </div>

                    <div className="gauge-card">
                      <GaugeChart 
                        value={parseFloat(memUsagePercent)} 
                        max={100} 
                        size={85}
                        label="Memory"
                      />
                      <div className="gauge-info">
                        <div className="gauge-info-label">GPU Memory</div>
                        <div className="gauge-info-value">
                          {formatBytes(metric.gpu_memory_used_mib)} / {formatBytes(metric.gpu_memory_total_mib)}
                        </div>
                        <div className="gauge-info-sub">
                          {formatBytes(metric.gpu_memory_free_mib)} available
                        </div>
                      </div>
                    </div>

                    <div className="gauge-card">
                      <GaugeChart 
                        value={getUsagePercentage(metric.host_memory_used_mib, metric.host_memory_total_mib)} 
                        max={100} 
                        size={85}
                        label="RAM"
                      />
                      <div className="gauge-info">
                        <div className="gauge-info-label">Host RAM</div>
                        <div className="gauge-info-value">
                          {formatBytes(metric.host_memory_used_mib)} / {formatBytes(metric.host_memory_total_mib)}
                        </div>
                        <div className="gauge-info-sub">
                          {formatBytes(metric.host_memory_total_mib - metric.host_memory_used_mib)} available
                        </div>
                      </div>
                    </div>
                  </div>

                  {metric.processes && metric.processes.length > 0 && (
                    <div className="processes-section">
                      <div className="processes-header">
                        <h4 className="processes-title">Running Processes ({metric.processes.length})</h4>
                      </div>
                      <div className="processes-grid">
                        {metric.processes.map((process, idx) => {
                          const processMemPercent = getUsagePercentage(process.used_mem_mib, metric.gpu_memory_total_mib);
                          return (
                            <div key={idx} className="process-card">
                              <div className="process-header">
                                <div className="process-pid-badge">PID {process.pid}</div>
                                <div className="process-name">{process.process_name}</div>
                              </div>
                              
                              {/* Process Memory Stats */}
                              <div className="process-memory-stats">
                                <div className="process-gauge-card">
                                  <GaugeChart 
                                    value={parseFloat(processMemPercent)} 
                                    max={100} 
                                    size={70}
                                    label="GPU RAM"
                                  />
                                  <div className="process-gauge-info">
                                    <div className="process-gauge-label">GPU Memory</div>
                                    <div className="process-gauge-value">
                                      {formatBytes(process.used_mem_mib)}
                                    </div>
                                    <div className="process-gauge-sub">
                                      of {formatBytes(metric.gpu_memory_total_mib)}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="process-gauge-card">
                                  <GaugeChart 
                                    value={process.process_ram_mib && metric.host_memory_total_mib ? 
                                      parseFloat((process.process_ram_mib / metric.host_memory_total_mib * 100).toFixed(1)) : 0} 
                                    max={100} 
                                    size={70}
                                    label="RAM"
                                  />
                                  <div className="process-gauge-info">
                                    <div className="process-gauge-label">Host RAM</div>
                                    <div className="process-gauge-value">
                                      {formatBytes(process.process_ram_mib || 0)}
                                    </div>
                                    <div className="process-gauge-sub">
                                      of {formatBytes(metric.host_memory_total_mib)}
                                    </div>
                                  </div>
                                </div>
                              </div>
                              
                              <div className="process-cmd" title={process.cmd}>
                                {process.cmd.length > 50 ? `${process.cmd.substring(0, 50)}...` : process.cmd}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
              </div>
            </div>
          </div>
        );
      })}
      
      {/* Manage GPU Panel - Rendered outside to float over content */}
      {manageModalOpen && selectedGPUName && (
        <ManageGPUModal
          gpuName={selectedGPUName}
          isOpen={true}
          onClose={handleManageClose}
          onUpdate={handleManageUpdate}
          buttonRef={{ current: editButtonRefs.current[selectedGPUName] }}
          azureUsersCache={azureUsersCache}
        />
      )}
    </div>
  );
}

export default GPUStats;

