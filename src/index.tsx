import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Temporary diagnostic aid for the mobile build: the WebView has no console
// visible to the user, so an uncaught error currently just leaves a blank
// white screen with no way to know why. Surface it directly in the DOM
// instead until remote debugging (chrome://inspect) is working.
function showFatalError(source: string, message: string, stack?: string) {
  const el = document.getElementById('root');
  if (!el) return;
  el.innerHTML = `
    <div style="padding:20px;font-family:monospace;font-size:12px;color:#fff;background:#300;white-space:pre-wrap;word-break:break-word;height:100%;overflow:auto;">
      <div style="font-size:16px;font-weight:bold;margin-bottom:10px;">Erreur (${source})</div>
      <div>${message}</div>
      ${stack ? `<div style="margin-top:10px;opacity:0.8;">${stack}</div>` : ''}
    </div>
  `;
}

window.addEventListener('error', (event) => {
  showFatalError('window.onerror', event.message, event.error?.stack);
});

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason;
  showFatalError('unhandledrejection', reason?.message ?? String(reason), reason?.stack);
});

class ErrorBoundary extends React.Component<{ children: React.ReactNode }> {
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    showFatalError('React render', error.message, error.stack + '\n' + info.componentStack);
  }
  render() {
    return this.props.children;
  }
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
