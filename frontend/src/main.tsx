import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
// Remove default index.css to let MUI Theme handle styles
// import './index.css' 
import { CssBaseline } from '@mui/material'

// Polyfill process for dependency compatibility
if (typeof window !== 'undefined') {
  window.process = window.process || { env: {} } as any;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CssBaseline />
    <App />
  </React.StrictMode>,
)
