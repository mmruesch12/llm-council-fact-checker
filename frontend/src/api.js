/**
 * API client for the LLM Council backend.
 */

// Use environment variable for API URL in production, fallback to localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = {
  /**
   * Get available models and default configuration.
   */
  async getModels() {
    const response = await fetch(`${API_BASE}/api/models`);
    if (!response.ok) {
      throw new Error('Failed to get models');
    }
    return response.json();
  },

  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Get all cataloged errors with summary statistics.
   */
  async getErrors() {
    const response = await fetch(`${API_BASE}/api/errors`);
    if (!response.ok) {
      throw new Error('Failed to get errors');
    }
    return response.json();
  },

  /**
   * Clear all cataloged errors.
   */
  async clearErrors() {
    const response = await fetch(`${API_BASE}/api/errors`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to clear errors');
    }
    return response.json();
  },

  /**
   * Export a conversation to Markdown format.
   * Downloads the file directly to the user's browser.
   */
  async exportConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/export`
    );
    if (!response.ok) {
      throw new Error('Failed to export conversation');
    }
    
    // Get the filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'conversation.md';
    if (contentDisposition) {
      // Match both quoted and unquoted filenames
      const match = contentDisposition.match(/filename=(?:"([^"]+)"|([^;\s]+))/);
      if (match) {
        filename = match[1] || match[2];
      }
    }
    
    // Get the markdown content
    const blob = await response.blob();
    
    // Create a download link and trigger it
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @param {object} modelConfig - Optional model configuration { councilModels, chairmanModel }
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent, modelConfig = {}) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          council_models: modelConfig.councilModels || null,
          chairman_model: modelConfig.chairmanModel || null,
          fact_checking_enabled: modelConfig.factCheckingEnabled !== undefined
            ? modelConfig.factCheckingEnabled
            : true,
        }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = ''; // Buffer for incomplete lines

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Append new chunk to buffer
      buffer += decoder.decode(value, { stream: true });
      
      // Split by newlines, but keep the last (potentially incomplete) part
      const lines = buffer.split('\n');
      // Save the last element (might be incomplete) back to buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
