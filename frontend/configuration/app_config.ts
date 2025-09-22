// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Frontend application configuration - SIMPLE and CLEAR
 * All settings in one place, easy to understand and modify
 */

export interface AppConfiguration {
  // API settings
  api: {
    baseUrl: string;
    timeout: number;
    maxFileSize: number;
  };

  // UI settings
  ui: {
    maxFileSizeMB: number;
    allowedFileTypes: string[];
    uploadTimeout: number;
  };

  // Features
  features: {
    fastProcessing: boolean;
    invoiceHistory: boolean;
    realTimeUpdates: boolean;
  };
}

// Default configuration
export const appConfig: AppConfiguration = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    timeout: 30000, // 30 seconds
    maxFileSize: 10 * 1024 * 1024, // 10MB
  },

  ui: {
    maxFileSizeMB: 10,
    allowedFileTypes: ['.pdf'],
    uploadTimeout: 30000,
  },

  features: {
    fastProcessing: true,
    invoiceHistory: true,
    realTimeUpdates: false,
  },
};

// Helper functions for configuration
export const getApiUrl = (endpoint: string): string => {
  return `${appConfig.api.baseUrl}${endpoint}`;
};

export const isFeatureEnabled = (feature: keyof AppConfiguration['features']): boolean => {
  return appConfig.features[feature];
};