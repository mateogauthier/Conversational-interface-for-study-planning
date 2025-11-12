import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import App from './App.jsx'
import { auth0Config } from './config/auth0Config'
import './i18n'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Auth0Provider {...auth0Config}>
      <App />
    </Auth0Provider>
  </StrictMode>,
)
