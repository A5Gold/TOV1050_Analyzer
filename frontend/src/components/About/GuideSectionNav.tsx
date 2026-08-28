import React from 'react';
import { Box, Link, Typography } from '@mui/material';

import type { GuideNavItem } from './aboutGuideContent';

interface GuideSectionNavProps {
  items: GuideNavItem[];
  label: string;
}

const GuideSectionNav: React.FC<GuideSectionNavProps> = ({ items, label }) => (
  <Box
    component="nav"
    aria-label={label}
    sx={{
      position: { md: 'sticky' },
      top: { md: 16 },
      alignSelf: { md: 'flex-start' },
      display: { xs: 'flex', md: 'block' },
      gap: 0.5,
      width: { xs: '100%', md: 184 },
      flexShrink: 0,
      overflowX: { xs: 'auto', md: 'visible' },
      pb: { xs: 1, md: 0 },
      pr: { md: 2 },
      borderRight: { md: 1 },
      borderColor: 'divider',
      scrollbarWidth: 'thin',
    }}
  >
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ display: { xs: 'none', md: 'block' }, mb: 1, fontWeight: 700 }}
    >
      本頁章節
    </Typography>
    {items.map((item) => (
      <Link
        key={item.id}
        href={`#${item.id}`}
        underline="hover"
        color="text.secondary"
        sx={{
          display: 'block',
          flexShrink: 0,
          px: 1,
          py: 0.75,
          borderRadius: 1,
          fontSize: '0.8125rem',
          fontWeight: 600,
          whiteSpace: 'nowrap',
          '&:hover': { color: 'primary.main', bgcolor: 'action.hover' },
          '&:focus-visible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: 2 },
        }}
      >
        {item.label}
      </Link>
    ))}
  </Box>
);

export default GuideSectionNav;
