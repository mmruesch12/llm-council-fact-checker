import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import ErrorCatalog from './components/ErrorCatalog';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentView, setCurrentView] = useState('chat'); // 'chat' or 'errors'

  // Model configuration state
  const [availableModels, setAvailableModels] = useState([]);
  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [modelsLoaded, setModelsLoaded] = useState(false);

  // Fact-checking toggle state
  const [factCheckingEnabled, setFactCheckingEnabled] = useState(true);

  // Streaming view mode: 'grid' for streaming quadrants, 'tabs' for traditional tab view
  const [streamingViewMode, setStreamingViewMode] = useState('grid');

  // Local storage keys for model persistence
  const STORAGE_KEYS = {
    councilModels: 'llm-council-selected-council-models',
    chairmanModel: 'llm-council-selected-chairman-model',
  };

  // Streaming state for live parallel responses
  const [streamingState, setStreamingState] = useState({
    isStreaming: false,
    currentStage: null,
    models: [],
    content: {
      stage1: {},     // { [instance]: "accumulated text" }
      fact_check: {},
      stage3: {},
      stage4: {}
    },
    cataloging: {
      isActive: false,
      errorsCataloged: null
    }
  });

  // Load conversations and models on mount
  useEffect(() => {
    loadConversations();
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      const availableModelIds = data.available_models.map(m => m.id);
      setAvailableModels(data.available_models);

      // Try to restore saved council models from localStorage
      const savedCouncil = localStorage.getItem(STORAGE_KEYS.councilModels);
      if (savedCouncil) {
        try {
          const parsed = JSON.parse(savedCouncil);
          // Validate that all saved models still exist in available models
          const validModels = parsed.filter(id => availableModelIds.includes(id));
          if (validModels.length > 0) {
            setCouncilModels(validModels);
          } else {
            setCouncilModels(data.default_council);
          }
        } catch {
          setCouncilModels(data.default_council);
        }
      } else {
        setCouncilModels(data.default_council);
      }

      // Try to restore saved chairman model from localStorage
      const savedChairman = localStorage.getItem(STORAGE_KEYS.chairmanModel);
      if (savedChairman && availableModelIds.includes(savedChairman)) {
        setChairmanModel(savedChairman);
      } else {
        setChairmanModel(data.default_chairman);
      }

      setModelsLoaded(true);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  // Persist council models to localStorage when changed
  useEffect(() => {
    if (modelsLoaded && councilModels.length > 0) {
      localStorage.setItem(STORAGE_KEYS.councilModels, JSON.stringify(councilModels));
    }
  }, [councilModels, modelsLoaded]);

  // Persist chairman model to localStorage when changed
  useEffect(() => {
    if (modelsLoaded && chairmanModel) {
      localStorage.setItem(STORAGE_KEYS.chairmanModel, chairmanModel);
    }
  }, [chairmanModel, modelsLoaded]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => {
        if (!prev || !prev.messages) return prev;
        return {
          ...prev,
          messages: [...prev.messages, userMessage],
        };
      });

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        fact_check: null,
        stage3: null,
        stage4: null,
        metadata: null,
        loading: {
          stage1: false,
          fact_check: false,
          stage3: false,
          stage4: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => {
        if (!prev || !prev.messages) return prev;
        return {
          ...prev,
          messages: [...prev.messages, assistantMessage],
        };
      });

      // Send message with streaming
      const modelConfig = {
        councilModels: councilModels,
        chairmanModel: chairmanModel,
        factCheckingEnabled: factCheckingEnabled,
      };
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: true,
              currentStage: 'stage1',
              models: event.models || councilModels,
              content: { ...prev.content, stage1: {} }
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage1_chunk':
            setStreamingState(prev => ({
              ...prev,
              content: {
                ...prev.content,
                stage1: {
                  ...prev.content.stage1,
                  [event.instance]: (prev.content.stage1[event.instance] || '') + event.text
                }
              }
            }));
            break;

          case 'stage1_complete':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: false,
              currentStage: null
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'fact_check_start':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: true,
              currentStage: 'fact_check',
              models: event.models || councilModels,
              content: { ...prev.content, fact_check: {} }
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.loading.fact_check = true;
              return { ...prev, messages };
            });
            break;

          case 'fact_check_chunk':
            setStreamingState(prev => ({
              ...prev,
              content: {
                ...prev.content,
                fact_check: {
                  ...prev.content.fact_check,
                  [event.instance]: (prev.content.fact_check[event.instance] || '') + event.text
                }
              }
            }));
            break;

          case 'fact_check_complete':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: false,
              currentStage: null
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.fact_check = event.data;
              lastMsg.metadata = {
                ...lastMsg.metadata,
                label_to_model: event.metadata.label_to_model,
                aggregate_fact_checks: event.metadata.aggregate_fact_checks,
              };
              lastMsg.loading.fact_check = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: true,
              currentStage: 'stage3',
              models: event.models || councilModels,
              content: { ...prev.content, stage3: {} }
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_chunk':
            setStreamingState(prev => ({
              ...prev,
              content: {
                ...prev.content,
                stage3: {
                  ...prev.content.stage3,
                  [event.instance]: (prev.content.stage3[event.instance] || '') + event.text
                }
              }
            }));
            break;

          case 'stage3_complete':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: false,
              currentStage: null
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.stage3 = event.data;
              lastMsg.metadata = {
                ...lastMsg.metadata,
                aggregate_rankings: event.metadata.aggregate_rankings,
              };
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage4_start':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: true,
              currentStage: 'stage4',
              models: event.models || [chairmanModel],
              content: { ...prev.content, stage4: {} }
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.loading.stage4 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage4_chunk':
            setStreamingState(prev => ({
              ...prev,
              content: {
                ...prev.content,
                stage4: {
                  ...prev.content.stage4,
                  [event.instance]: (prev.content.stage4[event.instance] || '') + event.text
                }
              }
            }));
            break;

          case 'stage4_complete':
            setStreamingState(prev => ({
              ...prev,
              isStreaming: false,
              currentStage: null
            }));
            setCurrentConversation((prev) => {
              if (!prev || !prev.messages || prev.messages.length === 0) return prev;
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (!lastMsg || !lastMsg.loading) return prev;
              lastMsg.stage4 = event.data;
              lastMsg.loading.stage4 = false;
              return { ...prev, messages };
            });
            break;

          case 'cataloging_start':
            setStreamingState(prev => ({
              ...prev,
              cataloging: {
                isActive: true,
                errorsCataloged: null
              }
            }));
            break;

          case 'cataloging_complete':
            setStreamingState(prev => ({
              ...prev,
              cataloging: {
                isActive: false,
                errorsCataloged: event.data?.errors_cataloged || 0
              }
            }));
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reset streaming state and reload conversations list
            setStreamingState({
              isStreaming: false,
              currentStage: null,
              models: [],
              content: { stage1: {}, fact_check: {}, stage3: {}, stage4: {} },
              cataloging: { isActive: false, errorsCataloged: null }
            });
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setStreamingState({
              isStreaming: false,
              currentStage: null,
              models: [],
              content: { stage1: {}, fact_check: {}, stage3: {}, stage4: {} },
              cataloging: { isActive: false, errorsCataloged: null }
            });
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      }, modelConfig);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => {
        if (!prev || !prev.messages || prev.messages.length < 2) return prev;
        return {
          ...prev,
          messages: prev.messages.slice(0, -2),
        };
      });
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      {currentView === 'chat' ? (
        <>
          <Sidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            availableModels={availableModels}
            councilModels={councilModels}
            chairmanModel={chairmanModel}
            onCouncilChange={setCouncilModels}
            onChairmanChange={setChairmanModel}
            onNavigateToErrors={() => setCurrentView('errors')}
          />
          <ChatInterface
            conversation={currentConversation}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            streamingState={streamingState}
            streamingViewMode={streamingViewMode}
            onViewModeChange={setStreamingViewMode}
            factCheckingEnabled={factCheckingEnabled}
            onFactCheckingToggle={setFactCheckingEnabled}
          />
        </>
      ) : (
        <ErrorCatalog onBack={() => setCurrentView('chat')} />
      )}
    </div>
  );
}

export default App;
