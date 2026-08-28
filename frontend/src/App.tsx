import { useState } from 'react';
import { Box, Typography } from '@mui/material';
import MainLayout, { ViewType } from './components/Layout/MainLayout';
import ExceptionGeneratorView from './views/ExceptionGeneratorView';
import HistoryCompareView from './views/HistoryCompareView';
import DatabaseRecordView from './views/DatabaseRecordView';
import MetadataEditorView from './views/MetadataEditorView';
import AboutView from './views/AboutView';
import WearCalculatorView from './views/WearCalculatorView';
import TrendAnalyzerView from './views/TrendAnalyzerView';
import CalculationView from './views/CalculationView';
import VersionDifferenceView from './views/VersionDifferenceView';

function App() {
  const [currentView, setCurrentView] = useState<ViewType>('about');

  const renderContent = () => {
    switch (currentView) {
      case 'generator':
        return <ExceptionGeneratorView />;
      case 'compare':
        return <HistoryCompareView />;
      case 'version-difference':
        return <VersionDifferenceView />;
      case 'database':
        return <DatabaseRecordView />;
      case 'metadata':
        return <MetadataEditorView />;
      case 'wear':
        return <WearCalculatorView />;
      case 'trend':
        return <TrendAnalyzerView />;
      case 'calculation':
        return <CalculationView />;
      case 'about':
        return <AboutView />;
      default:
        return <Box sx={{ p: 3 }}><Typography>Page Not Found</Typography></Box>;
    }
  };

  return (
    <MainLayout activeView={currentView} onViewChange={setCurrentView}>
      {renderContent()}
    </MainLayout>
  );
}

export default App;
