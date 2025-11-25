import './Sidebar.css';
import ModelSelector from './ModelSelector';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  availableModels,
  councilModels,
  chairmanModel,
  onCouncilChange,
  onChairmanChange,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
           New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} messages
              </div>
            </div>
          ))
        )}
      </div>

      {availableModels.length > 0 && (
        <ModelSelector
          availableModels={availableModels}
          councilModels={councilModels}
          chairmanModel={chairmanModel}
          onCouncilChange={onCouncilChange}
          onChairmanChange={onChairmanChange}
        />
      )}
    </div>
  );
}
