const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const axios = require('axios'); // For health check
const fs = require('fs');

// Global reference to prevent garbage collection
let mainWindow;
let apiProcess;
let backendStartError = null;
const DEV_PORT = Number(process.env.TOV1050_DEV_PORT || 5174);
const API_PORT = 8000;
const HEALTH_CHECK_URL = `http://127.0.0.1:${API_PORT}/api/health`;
const HEALTH_CHECK_INTERVAL_MS = 500;
// Backend startup can be slow on first launch (especially unpacking/loading
// the bundled executable). Keep the health check in the background so the UI
// is usable while the process finishes booting.
const HEALTH_CHECK_TIMEOUT_MS = 90000;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL(`http://localhost:${DEV_PORT}`);
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load from packaged app resources
    const indexPath = path.join(__dirname, '../frontend/dist/index.html');
    console.log('[Electron] Loading:', indexPath);
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

/**
 * Poll the backend health endpoint until it responds or timeout is reached.
 * Returns true if backend is ready, false if timed out.
 */
function waitForBackend() {
  return new Promise((resolve) => {
    const startTime = Date.now();
    console.log('[Electron] Waiting for backend to be ready...');

    const check = () => {
      // If backend process died, stop waiting
      if (backendStartError) {
        console.error('[Electron] Backend failed to start:', backendStartError);
        resolve(false);
        return;
      }

      axios.get(HEALTH_CHECK_URL, { timeout: 2000 })
        .then((response) => {
          if (response.data && response.data.status === 'ok') {
            const elapsed = Date.now() - startTime;
            console.log(`[Electron] Backend ready after ${elapsed}ms`);
            resolve(true);
          } else {
            scheduleNext();
          }
        })
        .catch(() => {
          scheduleNext();
        });
    };

    const scheduleNext = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed >= HEALTH_CHECK_TIMEOUT_MS) {
        console.error(`[Electron] Backend health check timed out after ${HEALTH_CHECK_TIMEOUT_MS}ms`);
        resolve(false);
      } else {
        setTimeout(check, HEALTH_CHECK_INTERVAL_MS);
      }
    };

    check();
  });
}

function startPythonBackend() {
  let backendPath;
  let cwd;
  backendStartError = null;

  if (process.env.NODE_ENV === 'development') {
    // Development mode: Use venv Python
    const pythonPath = path.join(__dirname, '../venv/Scripts/python.exe');
    cwd = path.join(__dirname, '../backend');

    console.log(`[Electron] Starting Python Backend (Development)...`);
    console.log(`[Electron] Python Path: ${pythonPath}`);
    console.log(`[Electron] CWD: ${cwd}`);

    apiProcess = spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
      cwd: cwd,
      stdio: 'pipe'
    });

  } else {
    // Production mode: Use bundled PyInstaller executable
    backendPath = path.join(process.resourcesPath, 'backend', 'backend_server.exe');
    cwd = path.join(process.resourcesPath, 'backend');

    console.log(`[Electron] Starting Python Backend (Production)...`);
    console.log(`[Electron] Backend Path: ${backendPath}`);

    // Check if backend exists
    if (!fs.existsSync(backendPath)) {
      const msg = `Backend executable not found at: ${backendPath}`;
      console.error(`[Electron] ${msg}`);
      backendStartError = msg;
      return;
    }

    // Portable app paths
    const appRoot = path.join(process.resourcesPath, '..');
    const configPath = path.join(process.resourcesPath, 'config');
    const dataDir = path.join(appRoot, 'data');
    const dbPath = path.join(dataDir, 'analysis.db');

    // Ensure data directory exists
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }

    // Create portable.txt marker
    const portableMarker = path.join(path.dirname(backendPath), 'portable.txt');
    if (!fs.existsSync(portableMarker)) {
        fs.writeFileSync(portableMarker, 'Portable mode marker - do not delete');
    }

    console.log(`[Electron] App Root: ${appRoot}`);
    console.log(`[Electron] Config Path: ${configPath}`);
    console.log(`[Electron] DB Path: ${dbPath}`);

    apiProcess = spawn(backendPath, [], {
      cwd: cwd,
      stdio: 'pipe',
      env: {
        ...process.env,
        CONFIG_PATH: configPath,
        DB_PATH: dbPath,
      }
    });
  }

  if (apiProcess) {
    apiProcess.on('error', (err) => {
      const msg = `Failed to start Python process: ${err.message}`;
      console.error(`[Electron] ${msg}`);
      backendStartError = msg;
    });

    apiProcess.stdout.on('data', (data) => {
      console.log(`[Python]: ${data}`);
    });

    apiProcess.stderr.on('data', (data) => {
      console.error(`[Python Error]: ${data}`);
    });

    apiProcess.on('close', (code) => {
      console.log(`[Electron] Python process exited with code ${code}`);
      if (code !== 0 && code !== null) {
        backendStartError = `Python backend exited with code ${code}`;
      }
    });
  }
}

app.on('ready', () => {
  startPythonBackend();
  // Create the window immediately; health polling must never block first paint.
  createWindow();

  waitForBackend().then((backendReady) => {
    if (!backendReady) {
      const detail = backendStartError
        ? `Error: ${backendStartError}`
        : `The backend server did not respond within ${HEALTH_CHECK_TIMEOUT_MS / 1000} seconds.`;
      // Do not show a modal dialog during startup. The frontend status indicator
      // will continue retrying and surface the connection state to the user.
      console.error(`[Electron] Backend unavailable after startup window was shown. ${detail}`);
    }
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  if (apiProcess) {
    apiProcess.kill();
  }
});

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow();
  }
});

ipcMain.handle('dialog:openFile', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [{ name: 'TOV1050 Data Files', extensions: ['csv', 'txt', 'xlsx'] }]
  });
  if (canceled) {
    return null;
  } else {
    return filePaths[0];
  }
});

ipcMain.handle('dialog:saveFile', async (event, data, defaultName) => {
  const { canceled, filePath } = await dialog.showSaveDialog({
    defaultPath: defaultName,
    filters: [
      { name: 'Excel Files', extensions: ['xlsx'] },
      { name: 'CSV Files', extensions: ['csv'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  if (canceled || !filePath) {
    return { success: false };
  }

  try {
    fs.writeFileSync(filePath, Buffer.from(data));
    return { success: true, filePath };
  } catch (error) {
    console.error('Failed to save file:', error);
    return { success: false, error: error.message };
  }
});
