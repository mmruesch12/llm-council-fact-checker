import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAuth();
    // Check for auth errors in URL params (from OAuth callback)
    const params = new URLSearchParams(window.location.search);
    const authError = params.get('auth_error');
    if (authError) {
      setError(getErrorMessage(authError));
      // Clear the URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const getErrorMessage = (errorCode) => {
    const messages = {
      'not_authorized': 'Your GitHub account is not authorized to access this application.',
      'invalid_state': 'Invalid OAuth state. Please try logging in again.',
      'no_code': 'Authorization code missing. Please try logging in again.',
      'token_exchange_failed': 'Failed to complete authentication. Please try again.',
      'user_fetch_failed': 'Failed to fetch user information. Please try again.',
    };
    return messages[errorCode] || `Authentication error: ${errorCode}`;
  };

  const checkAuth = async () => {
    try {
      setLoading(true);
      // First check if auth is enabled
      const status = await api.getAuthStatus();
      setAuthEnabled(status.enabled);
      
      if (status.enabled) {
        // Then try to get current user
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
      } else {
        // Auth disabled, set anonymous user
        setUser({ login: 'anonymous', auth_disabled: true });
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      // If auth status endpoint fails, assume auth is not required
      setUser({ login: 'anonymous', auth_disabled: true });
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    window.location.href = api.getLoginUrl();
  };

  const logout = () => {
    window.location.href = api.getLogoutUrl();
  };

  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    authEnabled,
    loading,
    error,
    isAuthenticated: !!user && !user.auth_disabled,
    login,
    logout,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
