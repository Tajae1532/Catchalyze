import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  beta_access?: boolean;
}

interface Account {
  id: string;
  name: string;
  slug: string;
}

interface AuthState {
  user: User | null;
  account: Account | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: () => void;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  const API_BASE_URL = import.meta.env.VITE_PUBLIC_BASE_URL || 'http://localhost:8000';

  const login = () => {
    window.location.href = `${API_BASE_URL}/auth/google`;
  };

  const logout = async (): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
      
      if (response.ok) {
        setUser(null);
        setAccount(null);
      }
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const checkAuth = async (): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        setAccount(data.account);
      } else {
        // Handle 401 and other auth errors gracefully
        setUser(null);
        setAccount(null);
      }
    } catch (error) {
      // Silently handle connection errors (API server not available)
      console.log('Auth service unavailable, continuing as guest');
      setUser(null);
      setAccount(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const contextValue: AuthContextType = {
    user,
    account,
    isAuthenticated,
    isLoading,
    login,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};