import './ResponseTime.css';

/**
 * Classify response time into speed categories.
 * Thresholds based on typical LLM response times:
 * - Fast: < 5 seconds
 * - Average: 5-15 seconds
 * - Slow: > 15 seconds
 */
function getSpeedClass(responseTimeMs) {
  if (responseTimeMs === null || responseTimeMs === undefined) return '';

  const seconds = responseTimeMs / 1000;

  if (seconds < 5) return 'speed-fast';
  if (seconds <= 15) return 'speed-average';
  return 'speed-slow';
}

function formatResponseTime(responseTimeMs) {
  if (responseTimeMs === null || responseTimeMs === undefined) return null;

  const seconds = responseTimeMs / 1000;

  if (seconds < 1) {
    return `${responseTimeMs}ms`;
  } else if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = (seconds % 60).toFixed(0);
    return `${minutes}m ${remainingSeconds}s`;
  }
}

export default function ResponseTime({ responseTimeMs, showLabel = false }) {
  if (responseTimeMs === null || responseTimeMs === undefined) {
    return null;
  }

  const speedClass = getSpeedClass(responseTimeMs);
  const formattedTime = formatResponseTime(responseTimeMs);

  return (
    <span className={`response-time ${speedClass}`} title={`Response time: ${responseTimeMs}ms`}>
      <svg className="clock-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 6 12 12 16 14"></polyline>
      </svg>
      {showLabel && <span className="time-label">Response:</span>}
      <span className="time-value">{formattedTime}</span>
    </span>
  );
}

export { getSpeedClass, formatResponseTime };
