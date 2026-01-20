import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Accordion from './Accordion';
import Stage1 from './Stage1';
import FactCheck from './FactCheck';
import Stage3 from './Stage3';
import Stage4 from './Stage4';
import StreamingGrid from './StreamingGrid';
import './ChatInterface.css';

function formatTimestamp(timestamp) {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Get stage info for display
function getStageInfo(stage, factCheckingEnabled = true) {
  if (factCheckingEnabled) {
    const stageMap = {
      stage1: { badge: '01', title: 'Individual Responses' },
      fact_check: { badge: '02', title: 'Fact-Checking' },
      stage3: { badge: '03', title: 'Peer Rankings' },
      stage4: { badge: '04', title: 'Final Council Answer' }
    };
    return stageMap[stage] || { badge: '??', title: 'Unknown Stage' };
  } else {
    // When fact-checking is disabled, adjust stage numbering
    const stageMap = {
      stage1: { badge: '01', title: 'Individual Responses' },
      stage3: { badge: '02', title: 'Peer Rankings' },
      stage4: { badge: '03', title: 'Final Council Answer' }
    };
    return stageMap[stage] || { badge: '??', title: 'Unknown Stage' };
  }
}

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  streamingState = { isStreaming: false, currentStage: null, models: [], content: {}, cataloging: { isActive: false, errorsCataloged: null } },
  streamingViewMode = 'grid',
  onViewModeChange = () => {},
  factCheckingEnabled = true,
  onFactCheckingToggle = () => {},
  onExportConversation = () => {},
  onToggleSidebar = () => {},
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Convert streaming content object to array for StreamingGrid
  const getStreamingContentArray = (stage) => {
    const content = streamingState.content[stage] || {};
    return streamingState.models.map((_, index) => content[index] || '');
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  const stageInfo = getStageInfo(streamingState.currentStage, factCheckingEnabled);
  const showStreamingGrid = streamingState.isStreaming && streamingViewMode === 'grid';

  return (
    <div className="chat-interface">
      {/* View Mode and Fact-Checking Toggles */}
      <div className="view-mode-toggle">
        <button className="hamburger-menu" onClick={onToggleSidebar} title="Toggle sidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        
        <div className="toggle-group">
          <span className="toggle-label">View Mode:</span>
          <button
            className={`toggle-btn ${streamingViewMode === 'grid' ? 'active' : ''}`}
            onClick={() => onViewModeChange('grid')}
            title="Show streaming responses in a grid layout"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <rect x="1" y="1" width="6" height="6" rx="1" />
              <rect x="9" y="1" width="6" height="6" rx="1" />
              <rect x="1" y="9" width="6" height="6" rx="1" />
              <rect x="9" y="9" width="6" height="6" rx="1" />
            </svg>
            Grid
          </button>
          <button
            className={`toggle-btn ${streamingViewMode === 'tabs' ? 'active' : ''}`}
            onClick={() => onViewModeChange('tabs')}
            title="Show responses in traditional tab layout"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <rect x="1" y="1" width="14" height="4" rx="1" />
              <rect x="1" y="7" width="14" height="8" rx="1" />
            </svg>
            Tabs
          </button>
        </div>

        <div className="toggle-separator"></div>

        <div className="toggle-group">
          <span className="toggle-label">Fact-Checking:</span>
          <button
            className={`toggle-btn fact-check-toggle ${factCheckingEnabled ? 'active' : ''}`}
            onClick={() => onFactCheckingToggle(!factCheckingEnabled)}
            title={factCheckingEnabled ? "Fact-checking is enabled (4 stages)" : "Fact-checking is disabled (3 stages)"}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              {factCheckingEnabled ? (
                <>
                  <path d="M7 2.75a.75.75 0 01.75-.75h.5a.75.75 0 01.75.75v3.5a.75.75 0 01-.75.75h-.5a.75.75 0 01-.75-.75v-3.5z"/>
                  <path d="M8 10a2 2 0 100-4 2 2 0 000 4z"/>
                  <path d="M8 14A6 6 0 108 2a6 6 0 000 12zm0-1.5A4.5 4.5 0 118 3.5a4.5 4.5 0 010 9z"/>
                </>
              ) : (
                <path d="M8 14A6 6 0 108 2a6 6 0 000 12zm0-1.5A4.5 4.5 0 118 3.5a4.5 4.5 0 010 9z"/>
              )}
            </svg>
            {factCheckingEnabled ? 'Enabled' : 'Disabled'}
          </button>
        </div>

        <div className="toggle-separator"></div>

        <div className="toggle-group">
          <button
            className="export-btn"
            onClick={onExportConversation}
            disabled={conversation.messages.length === 0}
            title="Export conversation to Markdown"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8.5 1.5A.5.5 0 0 1 9 1h5a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5a.5.5 0 0 1 0 1H2v12h12V2H9a.5.5 0 0 1-.5-.5z"/>
              <path d="M8 11a.5.5 0 0 1-.5-.5V4.707L5.354 6.854a.5.5 0 1 1-.708-.708l3-3a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 4.707V10.5A.5.5 0 0 1 8 11z"/>
            </svg>
            Export
          </button>
        </div>
      </div>

      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-header">
                    <span className="message-label">You</span>
                    {msg.timestamp && (
                      <span className="message-timestamp">{formatTimestamp(msg.timestamp)}</span>
                    )}
                  </div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-header">
                    <span className="message-label">LLM Council</span>
                    {msg.timestamp && (
                      <span className="message-timestamp">{formatTimestamp(msg.timestamp)}</span>
                    )}
                  </div>

                  {/* Stage 1: Individual Responses */}
                  {msg.loading?.stage1 && (
                    showStreamingGrid && streamingState.currentStage === 'stage1' ? (
                      <StreamingGrid
                        models={streamingState.models}
                        streamingContent={getStreamingContentArray('stage1')}
                        stageName={stageInfo.badge}
                        stageTitle={stageInfo.title}
                      />
                    ) : (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>Running Stage 1: Collecting individual responses...</span>
                      </div>
                    )
                  )}
                  {msg.stage1 && (
                    <Accordion
                      title="Individual Responses"
                      badge="01"
                      defaultExpanded={false}
                    >
                      <Stage1 responses={msg.stage1} />
                    </Accordion>
                  )}

                  {/* Stage 2: Fact-Checking */}
                  {msg.loading?.fact_check && (
                    showStreamingGrid && streamingState.currentStage === 'fact_check' ? (
                      <StreamingGrid
                        models={streamingState.models}
                        streamingContent={getStreamingContentArray('fact_check')}
                        stageName={stageInfo.badge}
                        stageTitle={stageInfo.title}
                      />
                    ) : (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>Running Stage 2: Fact-checking each other's responses...</span>
                      </div>
                    )
                  )}
                  {msg.fact_check && (
                    <Accordion
                      title="Fact-Checking"
                      badge="02"
                      variant="fact-check"
                      defaultExpanded={false}
                    >
                      <FactCheck
                        factChecks={msg.fact_check}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateFactChecks={msg.metadata?.aggregate_fact_checks}
                      />
                    </Accordion>
                  )}

                  {/* Stage 3: Peer Rankings */}
                  {msg.loading?.stage3 && (
                    showStreamingGrid && streamingState.currentStage === 'stage3' ? (
                      <StreamingGrid
                        models={streamingState.models}
                        streamingContent={getStreamingContentArray('stage3')}
                        stageName={stageInfo.badge}
                        stageTitle={stageInfo.title}
                      />
                    ) : (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>
                          Running Stage {factCheckingEnabled ? '3' : '2'}: Peer rankings
                          {factCheckingEnabled && ' (informed by fact-checks)'}...
                        </span>
                      </div>
                    )
                  )}
                  {msg.stage3 && (
                    <Accordion
                      title="Peer Rankings"
                      badge={factCheckingEnabled ? "03" : "02"}
                      variant="rankings"
                      defaultExpanded={false}
                    >
                      <Stage3
                        rankings={msg.stage3}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                      />
                    </Accordion>
                  )}

                  {/* Stage 4: Final Synthesis */}
                  {msg.loading?.stage4 && (
                    showStreamingGrid && streamingState.currentStage === 'stage4' ? (
                      <StreamingGrid
                        models={streamingState.models}
                        streamingContent={getStreamingContentArray('stage4')}
                        stageName={stageInfo.badge}
                        stageTitle={stageInfo.title}
                      />
                    ) : (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>
                          Running Stage {factCheckingEnabled ? '4' : '3'}: Final synthesis
                          {factCheckingEnabled && ' with fact-check validation'}...
                        </span>
                      </div>
                    )
                  )}
                  {msg.stage4 && (
                    <Accordion
                      title="Final Council Answer"
                      badge={factCheckingEnabled ? "04" : "03"}
                      variant="final"
                      defaultExpanded={true}
                    >
                      <Stage4 finalResponse={msg.stage4} />
                    </Accordion>
                  )}

                  {/* Error Cataloging Indicator - shows after Stage 4 completes */}
                  {index === conversation.messages.length - 1 && streamingState.cataloging?.isActive && (
                    <div className="cataloging-indicator">
                      <div className="cataloging-content">
                        <div className="spinner cataloging-spinner"></div>
                        <span>Cataloging errors for model improvement...</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
