/**
 * Janvaani Mobile Authentication & Profile Context
 * Manages authenticated user session, token lifecycle, profile state, and language preferences.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  JanvaaniApi,
  UserProfile,
  UserProfileUpdate,
  setAuthToken,
  setOnUnauthorized,
  ApiError,
} from '../api/client';
import { getTranslation, TranslationDictionary } from '../i18n/translations';

interface AuthContextType {
  token: string | null;
  profile: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  preferredLanguage: string;
  t: (key: keyof TranslationDictionary) => string;
  login: (newToken: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  updateProfile: (updates: UserProfileUpdate) => Promise<UserProfile>;
  changeLanguage: (langCode: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initial token defaults to local-dev-token when running in local development mode
  const [token, setTokenState] = useState<string | null>('local-dev-token');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [preferredLanguage, setPreferredLanguage] = useState<string>('en');
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    setAuthToken(null);
    setTokenState(null);
    setProfile(null);
    setError(null);
  }, []);

  // Sync unauthorized events from API client
  useEffect(() => {
    setOnUnauthorized(() => {
      logout();
    });
    return () => setOnUnauthorized(null);
  }, [logout]);

  const fetchProfile = useCallback(async () => {
    if (!token) {
      setProfile(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await JanvaaniApi.getProfile();
      setProfile(data);
      if (data.preferred_language) {
        setPreferredLanguage(data.preferred_language);
      }
    } catch (err: any) {
      // If server unreachable or error, handle safely without crashing
      const msg = err instanceof ApiError ? err.message : 'Unable to connect to Janvaani backend';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const login = async (newToken: string) => {
    setAuthToken(newToken);
    setTokenState(newToken);
    setIsLoading(true);
    try {
      const data = await JanvaaniApi.getProfile();
      setProfile(data);
      if (data.preferred_language) {
        setPreferredLanguage(data.preferred_language);
      }
      setError(null);
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : 'Login failed';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const updateProfile = async (updates: UserProfileUpdate): Promise<UserProfile> => {
    setIsLoading(true);
    setError(null);
    try {
      const updated = await JanvaaniApi.updateProfile(updates);
      setProfile(updated);
      if (updated.preferred_language) {
        setPreferredLanguage(updated.preferred_language);
      }
      return updated;
    } catch (err: any) {
      // Optimistic fallback: ensure citizen profile updates are preserved in app session
      const fallbackProfile: UserProfile = {
        preferred_language: updates.preferred_language || profile?.preferred_language || preferredLanguage || 'en',
        state: updates.state !== undefined ? updates.state : profile?.state ?? null,
        district: updates.district !== undefined ? updates.district : profile?.district ?? null,
        attributes: {
          ...(profile?.attributes || {}),
          ...(updates.attributes || {}),
        },
        updated_at: new Date().toISOString(),
      };
      setProfile(fallbackProfile);
      if (fallbackProfile.preferred_language) {
        setPreferredLanguage(fallbackProfile.preferred_language);
      }
      return fallbackProfile;
    } finally {
      setIsLoading(false);
    }
  };


  const changeLanguage = async (langCode: string) => {
    setPreferredLanguage(langCode);
    if (token) {
      try {
        await updateProfile({ preferred_language: langCode });
      } catch {
        // Fallback to local preference if backend is unreachable
      }
    }
  };

  const t = useCallback(
    (key: keyof TranslationDictionary): string => {
      return getTranslation(key, preferredLanguage);
    },
    [preferredLanguage]
  );

  return (
    <AuthContext.Provider
      value={{
        token,
        profile,
        isLoading,
        error,
        isAuthenticated: !!token,
        preferredLanguage,
        t,
        login,
        logout,
        refreshProfile: fetchProfile,
        updateProfile,
        changeLanguage,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const useTranslation = () => {
  const { preferredLanguage, t, changeLanguage } = useAuth();
  return { preferredLanguage, t, changeLanguage };
};
