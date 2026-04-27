import React from "react";

interface ThinkingMessageProps {
  agentName?: string;
  duration?: string;
}

export const ThinkingMessage: React.FC<ThinkingMessageProps> = ({ 
  agentName = "Assistant", 
  duration 
}) => {
  return (
    <div className="message assistant thinking">
      <div className="trace-header">
        <div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }}></div>
        <span className="trace-agent">{agentName} is thinking...</span>
        {duration && <span className="trace-time">{duration}</span>}
      </div>
      <div className="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  );
};
