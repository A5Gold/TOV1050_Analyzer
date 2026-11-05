import React from 'react';
import { Box, Table, TableBody, TableCell, TableContainer, TableRow, Typography } from '@mui/material';
import { metadataFormatRows, metadataPathDescription } from './aboutGuideContent';

const MetadataFormatGuide: React.FC = () => (
  <Box>
    <Typography variant="body2" sx={{ mb: 2, maxWidth: '76ch' }}>
      {metadataPathDescription}
    </Typography>
    <TableContainer>
      <Table size="small" aria-label="Wide metadata 格式與區間規則">
        <TableBody>{metadataFormatRows.map(({ cells }) => (
          <TableRow key={cells[0]}>
            <TableCell component="th" scope="row" sx={{ minWidth: 120 }}>{cells[0]}</TableCell>
            <TableCell>{cells[1]}</TableCell>
          </TableRow>
        ))}</TableBody>
      </Table>
    </TableContainer>
  </Box>
);

export default MetadataFormatGuide;
