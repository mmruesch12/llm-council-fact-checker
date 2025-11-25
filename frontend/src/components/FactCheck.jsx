import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './FactCheck.css';

// Helper to get display name from model info (handles both old string format and new {model, instance} format)
function getModelDisplayName(modelInfo, includeInstance = false) {
  if (!modelInfo) return null;
  // Handle new format: {model: "...", instance: N}
  if (typeof modelInfo === 'object' && modelInfo.model) {
    const shortName = modelInfo.model.split('/')[1] || modelInfo.model;
    return includeInstance && modelInfo.instance !== undefined
      ? `${shortName} #${modelInfo.instance + 1}`
      : shortName;
  }
  // Handle old format: just a string
  return modelInfo.split('/')[1] || modelInfo;
}

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, modelInfo]) => {
    const displayName = getModelDisplayName(modelInfo, true);
    result = result.replace(new RegExp(label, 'g'), `**${displayName}**`);
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

// Helper to check if there are duplicate models in the results
function hasDuplicateModels(results) {
  if (!results) return false;
  const models = results.map(r => r.model);
  return new Set(models).size !== models.length;
}

// Get display name for a fact-checker result
function getFactCheckerDisplayName(fc, factChecks) {
  const shortName = fc.model.split('/')[1] || fc.model;
  if (hasDuplicateModels(factChecks) && fc.instance !== undefined) {
    return `${shortName} #${fc.instance + 1}`;
  }
  return shortName;
}

export default function FactCheck({ factChecks, labelToModel, aggregateFactChecks }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!factChecks || factChecks.length === 0) {
    return null;
  }

  const showInstances = hasDuplicateModels(factChecks);

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
                  {agg.instance !== undefined && ` #${agg.instance + 1}`}
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
            {getFactCheckerDisplayName(fc, factChecks)}
            {fc.response_time_ms && (
              <ResponseTime responseTimeMs={fc.response_time_ms} />
            )}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="fact-check-header">
          <span className="fact-check-model">
            {factChecks[activeTab].model}
            {showInstances && factChecks[activeTab].instance !== undefined &&
              ` (Instance #${factChecks[activeTab].instance + 1})`}
          </span>
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
                        ? getModelDisplayName(labelToModel[label], true)
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
                  ? getModelDisplayName(labelToModel[factChecks[activeTab].parsed_summary.most_reliable], true)
                  : factChecks[activeTab].parsed_summary.most_reliable}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
