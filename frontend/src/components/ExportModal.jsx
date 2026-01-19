import { useState } from 'react';
import './ExportModal.css';

export default function ExportModal({ isOpen, onClose, onExport }) {
  const [selectedMode, setSelectedMode] = useState('all');

  if (!isOpen) return null;

  const handleExport = () => {
    onExport(selectedMode);
    onClose();
  };

  const exportOptions = [
    {
      value: 'all',
      label: 'All Results',
      description: 'Export all stages including individual responses, fact-checking, rankings, and final answer'
    },
    {
      value: 'rankings_and_final',
      label: 'Rankings & Final Answer',
      description: 'Export peer rankings and the final synthesized answer'
    },
    {
      value: 'final_only',
      label: 'Final Answer Only',
      description: 'Export only the final chairman answer for each query'
    }
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Export Options</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <p className="modal-description">Choose what to include in your export:</p>
          
          <div className="export-options">
            {exportOptions.map((option) => (
              <label key={option.value} className="export-option">
                <input
                  type="radio"
                  name="export-mode"
                  value={option.value}
                  checked={selectedMode === option.value}
                  onChange={(e) => setSelectedMode(e.target.value)}
                />
                <div className="option-content">
                  <div className="option-label">{option.label}</div>
                  <div className="option-description">{option.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="export-btn-primary" onClick={handleExport}>Export</button>
        </div>
      </div>
    </div>
  );
}
