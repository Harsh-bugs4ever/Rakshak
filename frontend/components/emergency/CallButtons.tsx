'use client';
import { shareMessage } from '@/lib/offline';
export interface CallButtonsProps { ambulance?: string; police?: string; coords?: { latitude: number; longitude: number } }
export default function CallButtons({ ambulance = '108', police = '112', coords }: CallButtonsProps) {
 async function share() {
 const text = shareMessage(coords);
 if (navigator.share) { try { await navigator.share({ text }); return; } catch (error) { if (error instanceof Error && error.name === 'AbortError') return; } }
 window.location.href = 'sms:?body=' + encodeURIComponent(text);
 }
 return <section className="actions" aria-label="Get help"><a className="ambulance" href={'tel:'+ambulance}><span>Call ambulance<small>Emergency medical help</small></span><strong>{ambulance} ↗</strong></a><div className="two-col"><a className="button" href={'tel:'+police}>Call police · {police}</a><button onClick={share}>Share location ↗</button></div><p className="caption">{coords ? 'Your location is ready to share.' : 'No location pin yet. Add a nearby landmark to your message.'} If 108 is unavailable, <a href="tel:112">call 112</a>.</p></section>;
}
