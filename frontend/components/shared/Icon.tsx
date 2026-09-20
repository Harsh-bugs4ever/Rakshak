import type { CSSProperties } from 'react';

export type IconName = 'shield' | 'phone' | 'pin' | 'arrow' | 'pulse' | 'heart' | 'check' | 'book' | 'sun' | 'moon' | 'hospital' | 'chevron';
const paths: Record<IconName, React.ReactNode> = {
  shield: <><path d="M12 3 4.5 6v5c0 4.6 3 7.8 7.5 10 4.5-2.2 7.5-5.4 7.5-10V6L12 3Z"/><path d="m8.5 11.5 2.5 2.5 4.5-5"/></>,
  phone: <path d="m7 3 3 5-2.5 2c1.4 3 3.5 5.1 6.5 6.5l2-2.5 5 3-1 3c-.4 1.2-2 1.5-3 1C8.4 18.8 5.2 15.6 3 7c-.5-1 0-2.6 1-3l3-1Z"/>,
  pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
  pulse: <path d="M2 12h5l3-8 4 16 3-8h5"/>,
  heart: <path d="M20 5c-2-2-6-1-8 2-2-3-6-4-8-2-4 4 0 9 8 15 8-6 12-11 8-15Z"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  book: <><path d="M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15"/></>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>,
  moon: <path d="M20 14A8 8 0 0 1 10 4a8.5 8.5 0 1 0 10 10Z"/>,
  hospital: <><path d="M5 21V5h14v16M2 21h20M9 21v-5h6v5M9 9h6m-3-3v6"/></>,
  chevron: <path d="m9 5 7 7-7 7"/>,
};
export default function Icon({ name, size = 22, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>{paths[name]}</svg>;
}
