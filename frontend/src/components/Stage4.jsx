import ReactMarkdown from 'react-markdown';
import ResponseTime from './ResponseTime';
import './Stage4.css';

export default function Stage4({ finalResponse }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage4">
      <h3 className="stage-title">Stage 4: Final Council Answer</h3>
      <div className="final-response">
        <div className="chairman-header">
          <span className="chairman-label">
            Chairman: {finalResponse.model.split('/')[1] || finalResponse.model}
          </span>
          <ResponseTime responseTimeMs={finalResponse.response_time_ms} />
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
