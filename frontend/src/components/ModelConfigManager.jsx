import { useState, useEffect } from 'react';
import { api } from '../api';
import './ModelConfigManager.css';

export default function ModelConfigManager({
  availableModels,
  councilModels,
  chairmanModel,
  onLoadConfig,
  onClose,
}) {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');
  const [makeDefault, setMakeDefault] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listModelConfigs();
      setConfigs(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!newConfigName.trim()) {
      setError('Please enter a configuration name');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await api.createModelConfig({
        name: newConfigName.trim(),
        council_models: councilModels,
        chairman_model: chairmanModel,
        is_default: makeDefault,
      });
      setNewConfigName('');
      setMakeDefault(false);
      setSaveDialogOpen(false);
      await loadConfigs();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleLoadConfig = async (config) => {
    onLoadConfig(config.council_models, config.chairman_model);
    onClose();
  };

  const handleDeleteConfig = async (configId) => {
    if (!confirm('Are you sure you want to delete this configuration?')) {
      return;
    }

    try {
      setError(null);
      await api.deleteModelConfig(configId);
      await loadConfigs();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSetDefault = async (configId) => {
    try {
      setError(null);
      await api.updateModelConfig(configId, { is_default: true });
      await loadConfigs();
    } catch (err) {
      setError(err.message);
    }
  };

  const getModelName = (modelId) => {
    const model = availableModels.find((m) => m.id === modelId);
    return model ? model.name : modelId;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content model-config-manager" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Model Configurations</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {error && <div className="error-message">{error}</div>}

          {/* Save current config button */}
          <div className="save-current-section">
            <button
              className="btn-primary"
              onClick={() => setSaveDialogOpen(!saveDialogOpen)}
            >
              {saveDialogOpen ? 'Cancel' : 'Save Current Configuration'}
            </button>
          </div>

          {/* Save dialog */}
          {saveDialogOpen && (
            <div className="save-dialog">
              <input
                type="text"
                placeholder="Configuration name"
                value={newConfigName}
                onChange={(e) => setNewConfigName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSaveConfig();
                  } else if (e.key === 'Escape') {
                    setSaveDialogOpen(false);
                    setNewConfigName('');
                  }
                }}
                autoFocus
              />
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={makeDefault}
                  onChange={(e) => setMakeDefault(e.target.checked)}
                />
                Set as default
              </label>
              <div className="save-dialog-actions">
                <button
                  className="btn-primary"
                  onClick={handleSaveConfig}
                  disabled={saving || !newConfigName.trim()}
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    setSaveDialogOpen(false);
                    setNewConfigName('');
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Saved configurations list */}
          <div className="configs-section">
            <h3>Saved Configurations</h3>
            {loading ? (
              <div className="loading-message">Loading configurations...</div>
            ) : configs.length === 0 ? (
              <div className="empty-message">No saved configurations yet</div>
            ) : (
              <div className="configs-list">
                {configs.map((config) => (
                  <div key={config.id} className="config-item">
                    <div className="config-header">
                      <div className="config-name">
                        {config.name}
                        {config.is_default && (
                          <span className="default-badge">Default</span>
                        )}
                      </div>
                      <div className="config-actions">
                        <button
                          className="btn-load"
                          onClick={() => handleLoadConfig(config)}
                          title="Load this configuration"
                        >
                          Load
                        </button>
                        {!config.is_default && (
                          <button
                            className="btn-set-default"
                            onClick={() => handleSetDefault(config.id)}
                            title="Set as default"
                          >
                            ⭐
                          </button>
                        )}
                        <button
                          className="btn-delete"
                          onClick={() => handleDeleteConfig(config.id)}
                          title="Delete configuration"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                    <div className="config-details">
                      <div className="config-detail">
                        <strong>Council:</strong>{' '}
                        {config.council_models.map(getModelName).join(', ')}
                      </div>
                      <div className="config-detail">
                        <strong>Chairman:</strong> {getModelName(config.chairman_model)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
