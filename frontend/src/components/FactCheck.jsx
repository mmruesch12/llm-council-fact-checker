import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './FactCheck.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

function getRatingClass(rating) {
  const normalized = rating?.toUpperCase();
  if (normalized === 'ACCURATE') return 'rating-accurate';
  if (normalized === 'MOSTLY ACCURATE') return 'rating-mostly-accurate';
  if (normalized === 'MIXED') return 'rating-mixed';
  if (normalized === 'MOSTLY INACCURATE') return 'rating-mostly-inaccurate';
  if (normalized === 'INACCURATE') return 'rating-inaccurate';
  return '';
}

export default function FactCheck({ factChecks, labelToModel, aggregateFactChecks }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!factChecks || factChecks.length === 0) {
    return null;
  }

  return (
    <div className="stage fact-check">
      <h3 className="stage-title">Stage 2: Fact-Checking</h3>

      {/* Aggregate Fact-Check Ratings */}
      {aggregateFactChecks && aggregateFactChecks.length > 0 && (
        <div className="aggregate-fact-checks">
          <h4>Aggregate Accuracy Ratings</h4>
          <p className="stage-description">
            Combined fact-check ratings across all reviewers (higher score is better):
          </p>
          <div className="aggregate-list">
            {aggregateFactChecks.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="fact-position">#{index + 1}</span>
                <span className="fact-model">
                  {agg.model.split('/')[1] || agg.model}
                </span>
                <span className={`fact-rating ${getRatingClass(agg.consensus_rating)}`}>
                  {agg.consensus_rating}
                </span>
                <span className="fact-score">
                  Score: {agg.average_score}/5
                </span>
                {agg.most_reliable_votes > 0 && (
                  <span className="fact-votes">
                    {agg.most_reliable_votes} "most reliable" vote{agg.most_reliable_votes > 1 ? 's' : ''}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <h4>Individual Fact-Check Analyses</h4>
      <p className="stage-description">
        Each model fact-checked all responses (anonymized as Response A, B, C, etc.).
        Below, model names are shown in <strong>bold</strong> for readability, but the original analysis used anonymous labels.
      </p>

      <div className="tabs">
        {factChecks.map((fc, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {fc.model.split('/')[1] || fc.model}
            {fc.response_time_ms && (
              <ResponseTime responseTimeMs={fc.response_time_ms} />
            )}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="fact-check-header">
          <span className="fact-check-model">{factChecks[activeTab].model}</span>
          <ResponseTime responseTimeMs={factChecks[activeTab].response_time_ms} />
        </div>
        <div className="fact-check-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(factChecks[activeTab].fact_check, labelToModel)}
          </ReactMarkdown>
        </div>

        {factChecks[activeTab].parsed_summary && (
          <div className="parsed-summary">
            <strong>Extracted Summary:</strong>
            {Object.keys(factChecks[activeTab].parsed_summary.ratings).length > 0 && (
              <div className="summary-ratings">
                {Object.entries(factChecks[activeTab].parsed_summary.ratings).map(([label, rating]) => (
                  <div key={label} className="summary-rating-item">
                    <span className="summary-label">
                      {labelToModel && labelToModel[label]
                        ? labelToModel[label].split('/')[1] || labelToModel[label]
                        : label}
                    </span>
                    <span className={`summary-rating ${getRatingClass(rating)}`}>
                      {rating}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {factChecks[activeTab].parsed_summary.most_reliable && (
              <div className="most-reliable">
                <strong>Most Reliable:</strong>{' '}
                {labelToModel && labelToModel[factChecks[activeTab].parsed_summary.most_reliable]
                  ? labelToModel[factChecks[activeTab].parsed_summary.most_reliable].split('/')[1] ||
                    labelToModel[factChecks[activeTab].parsed_summary.most_reliable]
                  : factChecks[activeTab].parsed_summary.most_reliable}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
