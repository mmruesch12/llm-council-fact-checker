import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

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
            {resp.model.split('/')[1] || resp.model}
            {resp.response_time_ms && (
              <ResponseTime responseTimeMs={resp.response_time_ms} />
            )}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-header">
          <span className="model-name">{responses[activeTab].model}</span>
          <ResponseTime responseTimeMs={responses[activeTab].response_time_ms} />
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
