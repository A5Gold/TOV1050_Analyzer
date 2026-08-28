import React, { useState, useMemo } from 'react';
import { 
  Box, Typography, Paper, List, ListItem, ListItemButton, 
  Chip, FormControl, InputLabel, Select, MenuItem,
  Divider, Stack
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import { AnalysisResponse, ExceptionRecord } from '../types/api';
import { safetyColors } from '../theme/AppTheme';

const LEVEL_COLORS: Record<string, string> = {
  'L1': safetyColors.l1, 
  'L2': safetyColors.l2, 
  'L3': safetyColors.l3, 
};

interface ExceptionListProps {
  result: AnalysisResponse | null;
  selectedExceptionId: string | null;
  onSelectException: (id: string | null) => void;
}

const ExceptionList = ({ result, selectedExceptionId, onSelectException }: ExceptionListProps) => {
  const [filterType, setFilterType] = useState<string>('All');
  const [filterLevel, setFilterLevel] = useState<string>('All');

  // Flatten and Filter Data
  const filteredItems = useMemo(() => {
    if (!result) return [];
    
    let all: ExceptionRecord[] = [];
    Object.values(result.exceptions).forEach(list => {
      all = [...all, ...list];
    });

    // Sort by Location
    all.sort((a, b) => a.maxLocation - b.maxLocation);

    return all.filter(item => {
      // Fix: Stagger filtering logic
      if (filterType !== 'All') {
        if (item['exception type'] !== filterType) return false;
      }
      
      if (filterLevel !== 'All' && item.level !== filterLevel) return false;
      return true;
    });
  }, [result, filterType, filterLevel]);

  // Extract Unique Types for Filter
  const exceptionTypes = useMemo(() => {
    if (!result) return [];
    // Get all unique types present in the data to ensure filter matches data
    const types = new Set<string>();
    Object.values(result.exceptions).forEach(list => {
      list.forEach(item => types.add(item['exception type']));
    });
    return Array.from(types).sort();
  }, [result]);

  if (!result) return null;

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        width: 320, 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        borderLeft: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper'
      }}
    >
      {/* Header & Filters */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.default' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <FilterListIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Typography variant="h6">Exceptions</Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Chip label={`${filteredItems.length} items`} size="small" />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Type</InputLabel>
            <Select 
              value={filterType} 
              label="Type"
              onChange={(e) => setFilterType(e.target.value)}
            >
              <MenuItem value="All">All Types</MenuItem>
              {exceptionTypes.map(t => (
                <MenuItem key={t} value={t}>{t}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <InputLabel>Level</InputLabel>
            <Select 
              value={filterLevel} 
              label="Level"
              onChange={(e) => setFilterLevel(e.target.value)}
            >
              <MenuItem value="All">All</MenuItem>
              <MenuItem value="L1">L1</MenuItem>
              <MenuItem value="L2">L2</MenuItem>
              <MenuItem value="L3">L3</MenuItem>
            </Select>
          </FormControl>
        </Box>
        
      </Box>

      {/* List */}
      <List sx={{ flexGrow: 1, overflow: 'auto', p: 0 }}>
        {filteredItems.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">No exceptions found.</Typography>
          </Box>
        ) : (
          filteredItems.map((item) => (
            <React.Fragment key={item.id}>
              <ListItem disablePadding>
                <ListItemButton 
                  selected={selectedExceptionId === item.id}
                  onClick={() => onSelectException(item.id)}
                  sx={{ 
                    flexDirection: 'column', 
                    alignItems: 'flex-start',
                    borderLeft: 4,
                    borderColor: LEVEL_COLORS[item.level] || 'grey.300',
                    py: 1.5
                  }}
                >
                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                      {item['exception type']}
                    </Typography>
                    <Stack direction="row" spacing={0.5}>
                      {item['Previous ID'] && (
                        <Chip 
                          label="R" 
                          size="small" 
                          color="secondary"
                          title={`Repeated: ${item['Previous ID']}`}
                          sx={{ height: 20, fontSize: '0.7rem', fontWeight: 'bold' }} 
                        />
                      )}
                      <Chip 
                        label={item.level} 
                        size="small" 
                        sx={{ 
                          height: 20, 
                          bgcolor: LEVEL_COLORS[item.level], 
                          color: 'white',
                          fontWeight: 'bold',
                          fontSize: '0.7rem'
                        }} 
                      />
                    </Stack>
                  </Box>
                  
                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                      ID: {item.id}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">
                      Loc: {item.maxLocation.toFixed(2)}m
                    </Typography>
                    <Typography variant="body2" color="text.primary" fontWeight="medium">
                      Val: {item.maxValue.toFixed(2)}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mt: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {item.Class} | {item['Track Type']}
                    </Typography>
                    {item['Tension Length'] && (
                      <Typography variant="caption" color="text.secondary">
                        TL: {item['Tension Length']}
                      </Typography>
                    )}
                  </Box>

                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mt: 0.5 }}>
                     <Typography variant="caption" color="text.secondary">
                      Len: {item.length.toFixed(2)}m
                    </Typography>
                    {item['Threshold Value'] && (
                      <Typography variant="caption" color="text.secondary">
                        Thresh: {item['Threshold Value']}
                      </Typography>
                    )}
                  </Box>
                </ListItemButton>
              </ListItem>
              <Divider component="li" />
            </React.Fragment>
          ))
        )}
      </List>
    </Paper>
  );
};

export default ExceptionList;