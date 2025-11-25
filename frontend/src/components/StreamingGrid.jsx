import ReactMarkdown from 'react-markdown';
import { encode } from 'gpt-tokenizer';
import './StreamingGrid.css';

// Helper to get display name from model string
function getDisplayName(model, instance, models) {
  const shortName = model.split('/')[1] || model;
  // Check if there are duplicates
  const duplicates = models.filter(m => m === model).length > 1;
  if (duplicates && instance !== undefined) {
    return `${shortName} #${instance + 1}`;
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

export default function StreamingGrid({
  models,
  streamingContent,
  stageName,
  stageTitle
}) {
  if (!models || models.length === 0) {
    return null;
  }

  const layout = getGridLayout(models.length);

  return (
    <div className="streaming-grid-container">
      <div className="streaming-grid-header">
        <span className="streaming-stage-badge">{stageName}</span>
        <span className="streaming-stage-title">{stageTitle}</span>
        <span className="streaming-indicator">
          <span className="streaming-dot"></span>
          Streaming...
        </span>
      </div>
      <div
        className="streaming-grid"
        style={{
          gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
        }}
      >
        {models.map((model, index) => {
          const content = streamingContent[index] || '';
          const displayName = getDisplayName(model, index, models);

          return (
            <div key={`${model}-${index}`} className="streaming-cell">
              <div className="streaming-cell-header">
                <span className="streaming-model-name">{displayName}</span>
                {content && (
                  <span className="streaming-char-count">
                    {encode(content).length} tokens
                  </span>
                )}
              </div>
              <div className="streaming-cell-content">
                {content ? (
                  <div className="markdown-content">
                    <ReactMarkdown>{content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="streaming-waiting">
                    <div className="streaming-waiting-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    Waiting for response...
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
