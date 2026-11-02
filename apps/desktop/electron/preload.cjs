const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('chiperDesktop', {
  getConnection: profile => ipcRenderer.invoke('chiper:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('chiper:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('chiper:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('chiper:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('chiper:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('chiper:window:openNewSession'),
  getBootProgress: () => ipcRenderer.invoke('chiper:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('chiper:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('chiper:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('chiper:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('chiper:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('chiper:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('chiper:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('chiper:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('chiper:profile:get'),
    set: name => ipcRenderer.invoke('chiper:profile:set', name)
  },
  api: request => ipcRenderer.invoke('chiper:api', request),
  notify: payload => ipcRenderer.invoke('chiper:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('chiper:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('chiper:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('chiper:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('chiper:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('chiper:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('chiper:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('chiper:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('chiper:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('chiper:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('chiper:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('chiper:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('chiper:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('chiper:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('chiper:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('chiper:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('chiper:openExternal', url),
  fetchLinkTitle: url => ipcRenderer.invoke('chiper:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('chiper:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('chiper:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('chiper:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('chiper:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('chiper:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('chiper:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('chiper:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('chiper:fs:gitRoot', startPath),
  worktrees: cwds => ipcRenderer.invoke('chiper:fs:worktrees', cwds),
  terminal: {
    dispose: id => ipcRenderer.invoke('chiper:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('chiper:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('chiper:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('chiper:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `chiper:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `chiper:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('chiper:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('chiper:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('chiper:open-updates', listener)
    return () => ipcRenderer.removeListener('chiper:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:deep-link', listener)
    return () => ipcRenderer.removeListener('chiper:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('chiper:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:window-state-changed', listener)
    return () => ipcRenderer.removeListener('chiper:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('chiper:focus-session', listener)
    return () => ipcRenderer.removeListener('chiper:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:notification-action', listener)
    return () => ipcRenderer.removeListener('chiper:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('chiper:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:backend-exit', listener)
    return () => ipcRenderer.removeListener('chiper:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('chiper:power-resume', listener)
    return () => ipcRenderer.removeListener('chiper:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:boot-progress', listener)
    return () => ipcRenderer.removeListener('chiper:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('chiper:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('chiper:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('chiper:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('chiper:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('chiper:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('chiper:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('chiper:version'),
  uninstall: {
    summary: () => ipcRenderer.invoke('chiper:uninstall:summary'),
    run: mode => ipcRenderer.invoke('chiper:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('chiper:updates:check'),
    apply: opts => ipcRenderer.invoke('chiper:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('chiper:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('chiper:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('chiper:updates:progress', listener)
      return () => ipcRenderer.removeListener('chiper:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('chiper:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('chiper:vscode-theme:search', query)
  }
})
