'use client';
import { useEffect, useState } from 'react';
import type { Stage } from '@/lib/types';
export interface StageCardProps { stage: Stage; defaultOpen?: boolean }
export default function StageCard({ stage, defaultOpen }: StageCardProps) {
 const [checked,setChecked] = useState<string[]>([]);
 const [storageError,setStorageError] = useState(false);
 const key = 'rakshak:stage:'+stage.stage_id;
 useEffect(() => { try { const saved: unknown = JSON.parse(localStorage.getItem(key) ?? '[]'); if (Array.isArray(saved)) setChecked(saved.filter((x): x is string => typeof x === 'string')); } catch { setStorageError(true); } },[key]);
 function toggle(item: string) { const next = checked.includes(item) ? checked.filter(x => x !== item) : [...checked,item]; setChecked(next); try { localStorage.setItem(key,JSON.stringify(next)); } catch { setStorageError(true); } }
 const count = stage.checklist.filter(item => checked.includes(item)).length;
 return <details className="stage card" open={defaultOpen}><summary><span className="stage-number">0{stage.order}</span><span><strong>{stage.title}</strong><small>{count} of {stage.checklist.length} completed</small></span><span className="expand">+</span></summary><p className="muted">{stage.subtitle}</p><progress value={count} max={stage.checklist.length} aria-label={stage.title+' progress'} /><div className="checklist">{stage.checklist.map(item => <label key={item}><input type="checkbox" checked={checked.includes(item)} onChange={() => toggle(item)} /><span>{item}</span></label>)}</div>{stage.details.map(detail => <p key={detail} className="detail-copy">{detail}</p>)}{storageError && <p role="status">Progress could not be saved on this device.</p>}</details>;
}
