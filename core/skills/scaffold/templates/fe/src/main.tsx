import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/app'
import './styles/globals.css'

const container = document.getElementById('root')
if (!container) {
  // index.html and this file disagree — fail here rather than rendering nothing
  // into a blank page and leaving the cause to the console.
  throw new Error('#root is missing from index.html')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
