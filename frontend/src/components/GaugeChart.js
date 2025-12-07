import React, { useState, useEffect } from 'react';
import '../styles/components/GaugeChart.css';

const GaugeChart = ({ value, max = 100, size = 100, label = '', showValue = true, animate = true }) => {
  const [animatedValue, setAnimatedValue] = useState(animate ? 0 : value);
  
  useEffect(() => {
    if (!animate) {
      setAnimatedValue(value);
      return;
    }
    
    // Reset to 0 when value changes significantly (new data)
    setAnimatedValue(0);
    
    // Animate to target value
    const duration = 1200; // 1.2 seconds
    const steps = 60;
    const stepValue = value / steps;
    const stepDuration = duration / steps;
    
    let currentStep = 0;
    const timer = setInterval(() => {
      currentStep++;
      if (currentStep >= steps) {
        setAnimatedValue(value);
        clearInterval(timer);
      } else {
        setAnimatedValue(stepValue * currentStep);
      }
    }, stepDuration);
    
    return () => clearInterval(timer);
  }, [value, animate]);
  
  const percentage = (animatedValue / max) * 100;
  const clampedPercentage = Math.min(Math.max(percentage, 0), 100);
  
  // Get color based on percentage with smooth gradient
  const getColor = () => {
    if (clampedPercentage <= 50) {
      return '#22c55e'; // Vibrant Green
    } else if (clampedPercentage <= 70) {
      return '#84cc16'; // Lime Green
    } else if (clampedPercentage <= 85) {
      return '#eab308'; // Yellow
    } else if (clampedPercentage <= 95) {
      return '#f97316'; // Orange
    } else {
      return '#ef4444'; // Red
    }
  };

  const color = getColor();
  const radius = 45;
  const strokeWidth = 10;
  const normalizedRadius = radius - strokeWidth / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  
  // Calculate stroke dash offset for 270 degrees (75% of circle)
  const gaugeCircumference = (circumference * 270) / 360;
  const strokeDashoffset = gaugeCircumference - (clampedPercentage / 100) * gaugeCircumference;

  return (
    <div className="gauge-container" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        className="gauge-svg"
      >
        {/* Background arc */}
        <circle
          cx="50"
          cy="50"
          r={normalizedRadius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          strokeDasharray={`${gaugeCircumference} ${circumference}`}
          strokeDashoffset="0"
          transform="rotate(-225 50 50)"
          strokeLinecap="round"
        />
        
        {/* Progress arc */}
        <circle
          cx="50"
          cy="50"
          r={normalizedRadius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${gaugeCircumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-225 50 50)"
          strokeLinecap="round"
          className="gauge-progress"
        />
        
        {/* Center circle */}
        <circle
          cx="50"
          cy="50"
          r="30"
          fill="white"
          stroke="#f3f4f6"
          strokeWidth="1"
        />
      </svg>
      
      {showValue && (
        <div className="gauge-value">
          <div className="gauge-percentage">{clampedPercentage.toFixed(0)}%</div>
          {label && <div className="gauge-label">{label}</div>}
        </div>
      )}
    </div>
  );
};

export default GaugeChart;

