import { useState } from 'react';
import './Accordion.css';

export default function Accordion({
  title,
  badge,
  defaultExpanded = false,
  variant = 'default',
  children,
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`accordion accordion-${variant} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <button
        className="accordion-header"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <div className="accordion-title-row">
          {badge && <span className="accordion-badge">{badge}</span>}
          <span className="accordion-title">{title}</span>
        </div>
        <span className="accordion-icon">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>
      <div className="accordion-content">
        <div className="accordion-inner">
          {children}
        </div>
      </div>
    </div>
  );
}
