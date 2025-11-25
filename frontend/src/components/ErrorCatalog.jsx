import { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../api';
import './ErrorCatalog.css';

function getErrorTypeClass(errorType) {
  const normalized = errorType?.toLowerCase().replace(/\s+/g, '-');
  return `error-type-${normalized}`;
}

function formatModelName(model) {
  return model?.split('/')[1] || model || 'Unknown';
}

function formatTimestamp(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ErrorCatalog({ onBack }) {
  const { theme, toggleTheme } = useTheme();
  const [errors, setErrors] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filterModel, setFilterModel] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('timestamp');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    loadErrors();
  }, []);

  const loadErrors = async () => {
    setIsLoading(true);
    try {
      const data = await api.getErrors();
      setErrors(data.errors || []);
      setSummary(data.summary || null);
    } catch (error) {
      console.error('Failed to load errors:', error);
    }
    setIsLoading(false);
  };

  const handleClearErrors = async () => {
    if (!window.confirm('Are you sure you want to clear all cataloged errors? This cannot be undone.')) {
      return;
    }
    try {
      await api.clearErrors();
      setErrors([]);
      setSummary({ total_errors: 0, by_model: {}, by_type: {}, by_model_and_type: {} });
    } catch (error) {
      console.error('Failed to clear errors:', error);
    }
  };

  // Get unique models and types for filters
  const uniqueModels = [...new Set(errors.map(e => e.model))].sort();
  const uniqueTypes = [...new Set(errors.map(e => e.error_type))].sort();

  // Filter and sort errors
  const filteredErrors = errors
    .filter(e => filterModel === 'all' || e.model === filterModel)
    .filter(e => filterType === 'all' || e.error_type === filterType)
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'timestamp') {
        comparison = new Date(a.timestamp) - new Date(b.timestamp);
      } else if (sortBy === 'model') {
        comparison = (a.model || '').localeCompare(b.model || '');
      } else if (sortBy === 'error_type') {
        comparison = (a.error_type || '').localeCompare(b.error_type || '');
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  return (
    <div className="error-catalog">
      <div className="error-catalog-header">
        <div className="header-left">
          <button className="back-btn" onClick={onBack}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            Back to Chat
          </button>
          <h1>Error Catalog</h1>
        </div>
        <div className="header-right">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1" x2="12" y2="3"/>
                <line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1" y1="12" x2="3" y2="12"/>
                <line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>
          <button className="refresh-btn" onClick={loadErrors} disabled={isLoading}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
          <button className="clear-btn" onClick={handleClearErrors} disabled={errors.length === 0}>
            Clear All
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-state">Loading error catalog...</div>
      ) : (
        <>
          {/* Summary Statistics */}
          {summary && summary.total_errors > 0 && (
            <div className="summary-section">
              <h2>Summary Statistics</h2>
              <div className="summary-grid">
                <div className="summary-card total">
                  <div className="summary-value">{summary.total_errors}</div>
                  <div className="summary-label">Total Errors</div>
                </div>

                <div className="summary-card">
                  <h3>By Model</h3>
                  <div className="breakdown-list">
                    {Object.entries(summary.by_model)
                      .sort(([, a], [, b]) => b - a)
                      .map(([model, count]) => (
                        <div key={model} className="breakdown-item">
                          <span className="breakdown-name">{formatModelName(model)}</span>
                          <span className="breakdown-count">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>

                <div className="summary-card">
                  <h3>By Error Type</h3>
                  <div className="breakdown-list">
                    {Object.entries(summary.by_type)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <div key={type} className="breakdown-item">
                          <span className={`breakdown-name ${getErrorTypeClass(type)}`}>{type}</span>
                          <span className="breakdown-count">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filters and Sort */}
          <div className="controls-section">
            <div className="filters">
              <div className="filter-group">
                <label>Model:</label>
                <select value={filterModel} onChange={(e) => setFilterModel(e.target.value)}>
                  <option value="all">All Models</option>
                  {uniqueModels.map(model => (
                    <option key={model} value={model}>{formatModelName(model)}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Error Type:</label>
                <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                  <option value="all">All Types</option>
                  {uniqueTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Sort By:</label>
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                  <option value="timestamp">Date</option>
                  <option value="model">Model</option>
                  <option value="error_type">Error Type</option>
                </select>
              </div>

              <button
                className="sort-order-btn"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
              >
                {sortOrder === 'asc' ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 5v14M5 12l7-7 7 7"/>
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 19V5M5 12l7 7 7-7"/>
                  </svg>
                )}
              </button>
            </div>

            <div className="results-count">
              Showing {filteredErrors.length} of {errors.length} errors
            </div>
          </div>

          {/* Error List */}
          <div className="error-list">
            {filteredErrors.length === 0 ? (
              <div className="empty-state">
                {errors.length === 0
                  ? 'No errors have been cataloged yet. Errors are automatically recorded during fact-checking.'
                  : 'No errors match the current filters.'}
              </div>
            ) : (
              filteredErrors.map((error) => (
                <div key={error.id} className="error-card">
                  <div className="error-header">
                    <span className="error-model">{formatModelName(error.model)}</span>
                    <span className={`error-type-badge ${getErrorTypeClass(error.error_type)}`}>
                      {error.error_type}
                    </span>
                    <span className="error-timestamp">{formatTimestamp(error.timestamp)}</span>
                  </div>
                  <div className="error-body">
                    <div className="error-field">
                      <label>Claim:</label>
                      <p>{error.claim}</p>
                    </div>
                    <div className="error-field">
                      <label>Explanation:</label>
                      <p>{error.explanation}</p>
                    </div>
                    {error.question_summary && (
                      <div className="error-field">
                        <label>Question Context:</label>
                        <p className="question-context">{error.question_summary}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
