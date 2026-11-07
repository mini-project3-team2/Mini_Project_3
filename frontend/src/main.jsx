import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { restore } from './services/api'

async function startMock() {
  if (!import.meta.env.DEV || import.meta.env.VITE_USE_MOCK !== 'true') return
  const { worker } = await import('./mocks/browser')
  await worker.start({ quiet: true, onUnhandledFrame: 'bypass' })
}

startMock()
  .catch((e) => console.error('[MSW] 시작 실패', e))
  .finally(() => {
  restore()
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
