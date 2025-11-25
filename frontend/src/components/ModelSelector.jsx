import { useState } from 'react';
import './ModelSelector.css';

const MAX_COUNCIL_MODELS = 4;

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

  // Count occurrences of each model
  const getModelCount = (modelId) => {
    return councilModels.filter((id) => id === modelId).length;
  };

  // Add a model (allows duplicates up to the limit)
  const addModel = (modelId) => {
    if (councilModels.length < MAX_COUNCIL_MODELS) {
      onCouncilChange([...councilModels, modelId]);
    }
  };

  // Remove a model by index
  const removeModelAtIndex = (index) => {
    if (councilModels.length > 1) {
      const newModels = [...councilModels];
      newModels.splice(index, 1);
      onCouncilChange(newModels);
    }
  };

  const getModelName = (modelId) => {
    const model = availableModels.find((m) => m.id === modelId);
    return model ? model.name : modelId;
  };

  const isAtLimit = councilModels.length >= MAX_COUNCIL_MODELS;

  return (
    <div className="model-selector">
      <button
        className={`model-selector-toggle ${isExpanded ? 'expanded' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="toggle-icon">{isExpanded ? '−' : '+'}</span>
        <span className="toggle-label">Model Configuration</span>
        <span className="model-count">{councilModels.length}/{MAX_COUNCIL_MODELS} models</span>
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
            <label className="section-label">Council Models (click to add, max {MAX_COUNCIL_MODELS})</label>
            <div className="selected-models">
              {councilModels.map((modelId, index) => (
                <span key={`${modelId}-${index}`} className="selected-model-tag">
                  {getModelName(modelId)}
                  {councilModels.length > 1 && (
                    <button
                      className="remove-model"
                      onClick={() => removeModelAtIndex(index)}
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
                    {models.map((model) => {
                      const count = getModelCount(model.id);
                      return (
                        <button
                          key={model.id}
                          className={`model-option ${count > 0 ? 'selected' : ''} ${isAtLimit ? 'disabled' : ''}`}
                          onClick={() => addModel(model.id)}
                          disabled={isAtLimit}
                          title={isAtLimit ? `Maximum ${MAX_COUNCIL_MODELS} models reached` : `Add ${model.name} to council`}
                        >
                          {model.name}
                          {count > 0 && <span className="model-count-badge">{count}</span>}
                        </button>
                      );
                    })}
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
