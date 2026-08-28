import { useState, useEffect } from 'react';
import { Chip, Tooltip, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import apiClient from '../api/client';

export default function SystemStatus() {
  const [status, setStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  
  const checkHealth = async () => {
    try {
      await apiClient.get('/health');
      setStatus('online');
    } catch (error) {
      setStatus('offline');
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (status === 'checking') {
    return (
      <Tooltip title="Backend connection has not been checked yet">
        <CircularProgress size={20} color="inherit" aria-label="Checking backend connection" />
      </Tooltip>
    );
  }

  return (
    <Tooltip title={status === 'online' ? "Backend online" : "Backend is unreachable. Click to retry."}>
      <Chip
        icon={status === 'online' ? <CheckCircleIcon /> : <ErrorIcon />}
        label={status === 'online' ? "System Ready" : "Backend Offline"}
        color={status === 'online' ? "success" : "error"}
        size="small"
        variant="outlined"
        onClick={status === 'offline' ? checkHealth : undefined}
        sx={{ 
          borderColor: 'rgba(255,255,255,0.5)', 
          color: 'white',
          '& .MuiChip-icon': { color: 'white' } 
        }}
      />
    </Tooltip>
  );
}
