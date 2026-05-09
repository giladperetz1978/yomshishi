import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const isGithubPagesHost = window.location.hostname.endsWith('github.io')
const configuredPublicAppUrl = String(import.meta.env.VITE_PUBLIC_APP_URL || '').trim().replace(/\/$/, '')

if (isGithubPagesHost && configuredPublicAppUrl) {
  try {
    const targetUrl = new URL(configuredPublicAppUrl)
    if (targetUrl.host !== window.location.host) {
      window.location.replace(`${configuredPublicAppUrl}/`)
      throw new Error('Redirecting to external app host...')
    }
  } catch (_error) {
    // Invalid URL in env var should not break app bootstrap.
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const swUrl = `${import.meta.env.BASE_URL}sw.js`
    navigator.serviceWorker.register(swUrl).catch((error) => {
      console.error('service worker registration failed', error)
    })
  })
}

