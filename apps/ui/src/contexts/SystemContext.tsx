import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

interface SystemStatus {
  paused: boolean;
  pause_reason: string;
  paused_tasks: string[];
  active_intents: number;
  registered_tools: string[];
}

interface SystemContextType {
  systemStatus: SystemStatus;
  pauseSystem: (reason?: string) => Promise<void>;
  resumeSystem: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

const SystemContext = createContext<SystemContextType | undefined>(undefined);

export const useSystem = () => {
  const context = useContext(SystemContext);
  if (context === undefined) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
};

interface SystemProviderProps {
  children: ReactNode;
}

const defaultStatus: SystemStatus = {
  paused: false,
  pause_reason: '',
  paused_tasks: [],
  active_intents: 0,
  registered_tools: []
};

export const SystemProvider: React.FC<SystemProviderProps> = ({ children }) => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>(defaultStatus);

  const refreshStatus = async () => {
    try {
      const response = await axios.get('/system/status');
      setSystemStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  };

  const pauseSystem = async (reason?: string) => {
    try {
      await axios.post('/system/control', {
        action: 'pause',
        reason: reason || 'User requested pause'
      });
      await refreshStatus();
    } catch (error) {
      console.error('Failed to pause system:', error);
      throw error;
    }
  };

  const resumeSystem = async () => {
    try {
      await axios.post('/system/control', {
        action: 'resume'
      });
      await refreshStatus();
    } catch (error) {
      console.error('Failed to resume system:', error);
      throw error;
    }
  };

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const value: SystemContextType = {
    systemStatus,
    pauseSystem,
    resumeSystem,
    refreshStatus
  };

  return (
    <SystemContext.Provider value={value}>
      {children}
    </SystemContext.Provider>
  );
};
