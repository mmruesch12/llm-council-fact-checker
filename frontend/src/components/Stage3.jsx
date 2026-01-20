import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './Stage2.css';

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

// Helper to check if there are duplicate models in the results
function hasDuplicateModels(results) {
  if (!results) return false;
  const models = results.map(r => r.model);
  return new Set(models).size !== models.length;
}

// Get display name for a ranking result
function getRankerDisplayName(rank, rankings) {
  const shortName = rank.model.split('/')[1] || rank.model;
  if (hasDuplicateModels(rankings) && rank.instance !== undefined) {
    return `${shortName} #${rank.instance + 1}`;
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

export default function Stage3({ rankings, labelToModel, aggregateRankings, viewMode = 'tabs' }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  const showInstances = hasDuplicateModels(rankings);
  const layout = getGridLayout(rankings.length);

  // Grid view
  if (viewMode === 'grid') {
    return (
      <div className="stage stage2">
        <h3 className="stage-title">Stage 3: Peer Rankings</h3>

        {aggregateRankings && aggregateRankings.length > 0 && (
          <div className="aggregate-rankings">
            <h4>Aggregate Rankings (Street Cred)</h4>
            <p className="stage-description">
              Combined results across all peer evaluations (lower score is better):
            </p>
            <div className="aggregate-list">
              {aggregateRankings.map((agg, index) => (
                <div key={index} className="aggregate-item">
                  <span className="rank-position">#{index + 1}</span>
                  <span className="rank-model">
                    {agg.model.split('/')[1] || agg.model}
                    {agg.instance !== undefined && ` #${agg.instance + 1}`}
                  </span>
                  <span className="rank-score">
                    Avg: {agg.average_rank.toFixed(2)}
                  </span>
                  <span className="rank-count">
                    ({agg.rankings_count} votes)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <h4>Individual Evaluations</h4>
        <p className="stage-description">
          Each model ranked all responses after reviewing the fact-check analyses.
          Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
        </p>

        <div 
          className="ranking-grid"
          style={{
            gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
          }}
        >
          {rankings.map((rank, index) => (
            <div key={index} className="ranking-grid-cell">
              <div className="grid-cell-header">
                <span className="grid-model-name">
                  {getRankerDisplayName(rank, rankings)}
                </span>
                <ResponseTime responseTimeMs={rank.response_time_ms} />
              </div>
              <div className="grid-cell-content markdown-content">
                <ReactMarkdown>
                  {deAnonymizeText(rank.ranking, labelToModel)}
                </ReactMarkdown>
                
                {rank.parsed_ranking && rank.parsed_ranking.length > 0 && (
                  <div className="parsed-ranking">
                    <strong>Extracted Ranking:</strong>
                    <ol>
                      {rank.parsed_ranking.map((label, i) => (
                        <li key={i}>
                          {labelToModel && labelToModel[label]
                            ? getModelDisplayName(labelToModel[label], true)
                            : label}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
              <div className="grid-cell-footer">
                <span className="grid-model-full-name">
                  {rank.model}
                  {showInstances && rank.instance !== undefined &&
                    ` (Instance #${rank.instance + 1})`}
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
    <div className="stage stage2">
      <h3 className="stage-title">Stage 3: Peer Rankings</h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model ranked all responses after reviewing the fact-check analyses.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getRankerDisplayName(rank, rankings)}
            {rank.response_time_ms && (
              <ResponseTime responseTimeMs={rank.response_time_ms} />
            )}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="ranking-header">
          <span className="ranking-model">
            {rankings[activeTab].model}
            {showInstances && rankings[activeTab].instance !== undefined &&
              ` (Instance #${rankings[activeTab].instance + 1})`}
          </span>
          <ResponseTime responseTimeMs={rankings[activeTab].response_time_ms} />
        </div>
        <div className="ranking-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(rankings[activeTab].ranking, labelToModel)}
          </ReactMarkdown>
        </div>

        {rankings[activeTab].parsed_ranking &&
         rankings[activeTab].parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {rankings[activeTab].parsed_ranking.map((label, i) => (
                <li key={i}>
                  {labelToModel && labelToModel[label]
                    ? getModelDisplayName(labelToModel[label], true)
                    : label}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {agg.model.split('/')[1] || agg.model}
                  {agg.instance !== undefined && ` #${agg.instance + 1}`}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
