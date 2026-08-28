import React from 'react';
import { Box, IconButton, Tab, Tabs, Tooltip } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';

export interface CycleTabItem {
  id: string;
  label: string;
}

interface CycleTabBarProps {
  tabs: CycleTabItem[];
  activeId: string;
  onChange: (id: string) => void;
  onAdd: () => void;
  onClose: (id: string) => void;
  onReset?: () => void;
  resetLabel?: string;
}

const CycleTabBar: React.FC<CycleTabBarProps> = ({
  tabs,
  activeId,
  onChange,
  onAdd,
  onClose,
  onReset,
  resetLabel = 'Reset Current Cycle',
}) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
      <Tabs
        value={activeId}
        onChange={(_, value) => onChange(value)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ flexGrow: 1, minHeight: 42 }}
      >
        {tabs.map((tab) => (
          <Tab
            key={tab.id}
            value={tab.id}
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {tab.label}
                {tabs.length > 1 && (
                  <IconButton
                    size="small"
                    component="span"
                    onClick={(e) => {
                      e.stopPropagation();
                      onClose(tab.id);
                    }}
                    sx={{ p: 0.25 }}
                  >
                    <CloseIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                )}
              </Box>
            }
            sx={{ minHeight: 42, textTransform: 'none' }}
          />
        ))}
      </Tabs>

      <Tooltip title="Add cycle tab">
        <IconButton onClick={onAdd} size="small" sx={{ mr: 1 }}>
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      {onReset && (
        <Tooltip title={resetLabel}>
          <IconButton aria-label={resetLabel} onClick={onReset} size="small" sx={{ mr: 1 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Box>
  );
};

export default CycleTabBar;
