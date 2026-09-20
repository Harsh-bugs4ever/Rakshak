/**
 * App shell.
 *
 * Deliberately thin: no onboarding, no splash, no login. The Emergency tab must
 * be usable by someone who installed the app four seconds ago.
 *
 * Design tokens and the full layout spec live in design/emergency-tab.md.
 */

import type { Metadata, Viewport } from 'next';
import TabBar from '@/components/shared/TabBar';
import OfflineStatus from '@/components/shared/OfflineStatus';
import { CompanionPanel } from '@/components/shared/BrandHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'Rakshak',
  description: 'Road accident help: what to do right now, and what comes after.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // viewportFit covers the notch; the tab bar uses safe-area insets.
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F6F7F9' },
    { media: '(prefers-color-scheme: dark)', color: '#0B0E13' },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell"><CompanionPanel /><main className="app">{children}<OfflineStatus /></main></div>
        <TabBar />
      </body>
    </html>
  );
}
