import { useState } from 'react';
import './ModelSelector.css';

export default function ModelSelector({
  availableModels,
  councilModels,
  chairmanModel,
  onCouncilChange,
  onChairmanChange,
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Group models by provider
  const modelsByProvider = availableModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {});

  const toggleModel = (modelId) => {
    if (councilModels.includes(modelId)) {
      // Don't allow removing if it's the last model
      if (councilModels.length > 1) {
        onCouncilChange(councilModels.filter((id) => id !== modelId));
      }
    } else {
      onCouncilChange([...councilModels, modelId]);
    }
  };

  const getModelName = (modelId) => {
    const model = availableModels.find((m) => m.id === modelId);
    return model ? model.name : modelId;
  };

  return (
    <div className="model-selector">
      <button
        className={`model-selector-toggle ${isExpanded ? 'expanded' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="toggle-icon">{isExpanded ? '−' : '+'}</span>
        <span className="toggle-label">Model Configuration</span>
        <span className="model-count">{councilModels.length} models</span>
      </button>

      {isExpanded && (
        <div className="model-selector-content">
          {/* Chairman Selection */}
          <div className="chairman-section">
            <label className="section-label">Chairman Model</label>
            <select
              className="chairman-select"
              value={chairmanModel}
              onChange={(e) => onChairmanChange(e.target.value)}
            >
              {availableModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          {/* Council Models Selection */}
          <div className="council-section">
            <label className="section-label">Council Models</label>
            <div className="selected-models">
              {councilModels.map((modelId) => (
                <span key={modelId} className="selected-model-tag">
                  {getModelName(modelId)}
                  {councilModels.length > 1 && (
                    <button
                      className="remove-model"
                      onClick={() => toggleModel(modelId)}
                    >
                      ×
                    </button>
                  )}
                </span>
              ))}
            </div>

            <div className="model-groups">
              {Object.entries(modelsByProvider).map(([provider, models]) => (
                <div key={provider} className="model-group">
                  <div className="provider-name">{provider}</div>
                  <div className="provider-models">
                    {models.map((model) => (
                      <button
                        key={model.id}
                        className={`model-option ${
                          councilModels.includes(model.id) ? 'selected' : ''
                        }`}
                        onClick={() => toggleModel(model.id)}
                      >
                        {model.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
