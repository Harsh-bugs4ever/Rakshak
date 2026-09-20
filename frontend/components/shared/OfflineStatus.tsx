'use client';
import { useEffect, useState } from 'react';

export default function OfflineStatus() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return;
    let active = true;
    navigator.serviceWorker.register('/service-worker.js')
      .then(() => navigator.serviceWorker.ready)
      .then(() => { if (active) setReady(true); })
      .catch(() => { /* The loaded app still has bundled reference content. */ });
    return () => { active = false; };
  }, []);
  return ready ? <p className="offline-status caption" role="status">Emergency and Aftermath screens saved for offline use.</p> : null;
}
