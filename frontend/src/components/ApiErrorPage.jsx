import './ApiErrorPage.css';

/**
 * Error page displayed when the API is unreachable (e.g., CORS errors, network issues).
 * Provides clear feedback to the user and troubleshooting information.
 */
function ApiErrorPage({ error, apiUrl }) {
  const isCorsError = error?.message?.includes('CORS') || 
                      error?.message?.includes('cors') ||
                      error?.message?.includes('Access-Control');
  
  const isNetworkError = error?.message?.includes('Failed to fetch') ||
                         error?.message?.includes('NetworkError') ||
                         error?.message?.includes('network');

  return (
    <div className="api-error-page">
      <div className="api-error-container">
        <div className="api-error-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        
        <h1 className="api-error-title">Unable to Connect to API</h1>
        
        <p className="api-error-description">
          {isCorsError && (
            <>The application cannot connect to the backend API due to a <strong>CORS configuration issue</strong>.</>
          )}
          {isNetworkError && !isCorsError && (
            <>The application cannot connect to the backend API. Please check your network connection.</>
          )}
          {!isCorsError && !isNetworkError && (
            <>The application cannot connect to the backend API.</>
          )}
        </p>

        <div className="api-error-details">
          <div className="error-detail-item">
            <span className="error-detail-label">API URL:</span>
            <code className="error-detail-value">{apiUrl || 'Not configured'}</code>
          </div>
          
          {error && (
            <div className="error-detail-item">
              <span className="error-detail-label">Error:</span>
              <code className="error-detail-value">{error.message || 'Unknown error'}</code>
            </div>
          )}
        </div>

        {isCorsError && (
          <div className="api-error-solution">
            <h2>How to Fix This</h2>
            <p>The backend needs to be configured to allow requests from this domain:</p>
            <ol>
              <li>Set the <code>FRONTEND_URL</code> environment variable on the backend to: <code>{window.location.origin}</code></li>
              <li>Restart the backend service</li>
              <li>Refresh this page</li>
            </ol>
            <p className="solution-note">
              <strong>Note:</strong> If you're the developer, check the backend's CORS configuration in <code>backend/main.py</code>
            </p>
          </div>
        )}

        {isNetworkError && !isCorsError && (
          <div className="api-error-solution">
            <h2>What to Check</h2>
            <ul>
              <li>Is the backend service running?</li>
              <li>Is your network connection stable?</li>
              <li>Is the API URL correct?</li>
              <li>Try refreshing the page</li>
            </ul>
          </div>
        )}

        <button 
          className="api-error-retry"
          onClick={() => window.location.reload()}
        >
          Retry Connection
        </button>
      </div>
    </div>
  );
}

export default ApiErrorPage;
