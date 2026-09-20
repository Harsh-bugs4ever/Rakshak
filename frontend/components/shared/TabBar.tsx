'use client';
import { usePathname } from 'next/navigation';

const tabs = [
  { href: '/emergency', title: 'Emergency', subtitle: 'First minutes' },
  { href: '/aftermath', title: 'Aftermath', subtitle: 'The road ahead' },
];

export default function TabBar() {
  const path = usePathname();
  // Document navigation lets the service worker serve either cached screen
  // without depending on Next.js RSC requests when the device is offline.
  return <nav className="tab-bar" aria-label="Main navigation">
    {tabs.map(tab => <a key={tab.href} href={tab.href} aria-current={path === tab.href ? 'page' : undefined}>
      <strong>{tab.title}</strong><small>{tab.subtitle}</small>
    </a>)}
  </nav>;
}
