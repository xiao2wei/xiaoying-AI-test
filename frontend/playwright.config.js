import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests',
  timeout: 20000,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: '../examples/submission/web-ui/frontend-tests.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : undefined) },
  },
  webServer: { command: 'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173 --strictPort', url: 'http://127.0.0.1:4173', reuseExistingServer: false },
})
