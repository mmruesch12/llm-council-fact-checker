/**
 * Utilities for detecting and handling API errors.
 */

/**
 * Detect if an error is a CORS-related error.
 * @param {Error|string} error - The error object or message
 * @returns {boolean} True if this appears to be a CORS error
 */
export function isCorsError(error) {
  const message = typeof error === 'string' ? error : (error?.message || '');
  return message.includes('CORS') || 
         message.includes('cors') || 
         message.includes('Access-Control');
}

/**
 * Detect if an error is a network-related error.
 * @param {Error|string} error - The error object or message
 * @returns {boolean} True if this appears to be a network error
 */
export function isNetworkError(error) {
  const message = typeof error === 'string' ? error : (error?.message || '');
  // Match specific network error patterns
  return message.includes('Failed to fetch') ||
         message.includes('NetworkError') ||
         message.includes('Network request failed') ||
         message.includes('net::');
}

/**
 * Check if an error prevents API connectivity.
 * @param {Error|string} error - The error object or message
 * @returns {boolean} True if this is a critical connection error
 */
export function isApiConnectionError(error) {
  return isCorsError(error) || isNetworkError(error);
}
