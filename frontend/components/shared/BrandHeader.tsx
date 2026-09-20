'use client';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Icon from './Icon';

export default function BrandHeader() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let theme: string | null = null;
    try { theme = localStorage.getItem('rakshak:theme'); } catch {}
    const isDark = theme ? theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
    setDark(isDark);
  }, []);
  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? 'dark' : 'light';
    try { localStorage.setItem('rakshak:theme', next ? 'dark' : 'light'); } catch {}
  }
  return <header className="brand"><a href="/emergency" className="brand-home" aria-label="Rakshak emergency home"><span className="brand-mark"><Icon name="shield" size={25}/></span><strong>rakshak<span>HERE WHEN IT MATTERS</span></strong></a><button className="theme-toggle" onClick={toggleTheme} aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}><Icon name={dark ? 'sun' : 'moon'} size={19}/></button></header>;
}

export function CompanionPanel() {
  const aftermath = usePathname() === '/aftermath';
  return <aside className="companion">
    <div className="companion-brand"><Icon name="shield" size={28}/><span>rakshak.</span></div>
    <p className="eyebrow">A little clarity. A lot of care.</p>
    <h2>{aftermath ? <>The road ahead.<br/><em>You’re not alone.</em></> : <>In a difficult moment,<br/><em>a steady hand.</em></>}</h2>
    <p className="companion-description">{aftermath ? 'A place for the next step, the right document, and the people who can help.' : 'Simple, practical support for the first minutes after an accident—and everything that follows.'}</p>
    <div className="care-illustration" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="care-emblem"><Icon name={aftermath ? 'heart' : 'shield'} size={60}/></div><span className="orbit-label label-one"><Icon name="check" size={14}/> One step at a time</span><span className="orbit-label label-two"><span/> Here to help</span></div>
    <nav className="companion-nav" aria-label="Your support journey"><a href="/emergency" aria-current={!aftermath ? 'page' : undefined}><span>01</span><div><strong>The first minutes</strong><small>Emergency help</small></div><Icon name="arrow" size={18}/></a><a href="/aftermath" aria-current={aftermath ? 'page' : undefined}><span>02</span><div><strong>The road after</strong><small>Family support</small></div><Icon name="arrow" size={18}/></a></nav>
    <p className="companion-footer">Built with care. For people who care.<br/><span>Road accident support · India</span></p>
  </aside>;
}
