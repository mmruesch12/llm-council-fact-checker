import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './Stage1.css';

// Helper to check if there are duplicate models in the responses
function hasDuplicateModels(responses) {
  const models = responses.map(r => r.model);
  return new Set(models).size !== models.length;
}

// Get display name with optional instance number
function getDisplayName(resp, responses) {
  const shortName = resp.model.split('/')[1] || resp.model;
  // Only show instance number if there are duplicates
  if (hasDuplicateModels(responses) && resp.instance !== undefined) {
    return `${shortName} #${resp.instance + 1}`;
  }
  return shortName;
}

// Calculate grid layout based on number of models
function getGridLayout(count) {
  if (count <= 1) return { cols: 1, rows: 1 };
  if (count === 2) return { cols: 2, rows: 1 };
  if (count <= 4) return { cols: 2, rows: 2 };
  if (count <= 6) return { cols: 3, rows: 2 };
  if (count <= 9) return { cols: 3, rows: 3 };
  return { cols: 4, rows: Math.ceil(count / 4) };
}

export default function Stage1({ responses, viewMode = 'tabs' }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  const showInstances = hasDuplicateModels(responses);
  const layout = getGridLayout(responses.length);

  // Grid view
  if (viewMode === 'grid') {
    return (
      <div className="stage stage1">
        <h3 className="stage-title">Stage 1: Individual Responses</h3>
        
        <div 
          className="response-grid"
          style={{
            gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
          }}
        >
          {responses.map((resp, index) => (
            <div key={index} className="response-grid-cell">
              <div className="grid-cell-header">
                <span className="grid-model-name">
                  {getDisplayName(resp, responses)}
                </span>
                <ResponseTime responseTimeMs={resp.response_time_ms} />
              </div>
              <div className="grid-cell-content markdown-content">
                <ReactMarkdown>{resp.response}</ReactMarkdown>
              </div>
              <div className="grid-cell-footer">
                <span className="grid-model-full-name">
                  {resp.model}
                  {showInstances && resp.instance !== undefined &&
                    ` (Instance #${resp.instance + 1})`}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Tabs view (default)
  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getDisplayName(resp, responses)}
            {resp.response_time_ms && (
              <ResponseTime responseTimeMs={resp.response_time_ms} />
            )}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-header">
          <span className="model-name">
            {responses[activeTab].model}
            {showInstances && responses[activeTab].instance !== undefined &&
              ` (Instance #${responses[activeTab].instance + 1})`}
          </span>
          <ResponseTime responseTimeMs={responses[activeTab].response_time_ms} />
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
