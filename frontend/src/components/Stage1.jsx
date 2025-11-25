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

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  const showInstances = hasDuplicateModels(responses);

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
