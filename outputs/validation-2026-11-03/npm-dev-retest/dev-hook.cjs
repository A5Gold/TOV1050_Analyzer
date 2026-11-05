// Test-only CDP access and download destination for the npm-run-dev Electron.
if (process.versions.electron && process.type === 'browser') {
  const Module = require('node:module');
  const load = Module._load;
  let installed = false;
  Module._load = function(request, ...args) {
    const value = load.call(this, request, ...args);
    if (request === 'electron' && value.app && !installed) {
      installed = true;
      install(value);
    }
    return value;
  };
}
function install({ app, dialog }) {
  const fs = require('node:fs');
  const path = require('node:path');
  app.commandLine.appendSwitch('remote-debugging-port', '9237');
  app.setPath('userData', path.join(__dirname, 'user-data'));
  dialog.showOpenDialog = async () => ({ canceled: false,
    filePaths: [fs.readFileSync(path.join(__dirname, 'selected-source.txt'), 'utf8').trim()] });
  app.whenReady().then(() => app.on('web-contents-created', (_event, contents) => {
    contents.session.on('will-download', (_event, item) => {
      item.setSavePath(path.join(__dirname, item.getFilename()));
    });
  }));
}
