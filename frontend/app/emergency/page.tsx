'use client';
import { useEffect, useState } from 'react';
import BrandHeader from '@/components/shared/BrandHeader';
import Icon from '@/components/shared/Icon';
import CallButtons from '@/components/emergency/CallButtons';
import TriageQuestion from '@/components/emergency/TriageQuestion';
import StepCards from '@/components/emergency/StepCards';
import ResourceList from '@/components/aftermath/ResourceList';
import AskBar from '@/components/shared/AskBar';
import { getProtocol } from '@/lib/api';
import { protocolForTriage, GOOD_SAMARITAN_POINTS } from '@/lib/offline';
import type { Protocol, TriageAnswer } from '@/lib/types';
export default function EmergencyPage() {
 const [answer,setAnswer] = useState<TriageAnswer>(); const [protocol,setProtocol] = useState<Protocol>(); const [saved,setSaved] = useState(true);
 const [coords,setCoords] = useState<{latitude:number;longitude:number}>();
 const [resources,setResources] = useState(false);
 useEffect(() => { try { const value = sessionStorage.getItem('rakshak:triage'); if (value === 'yes' || value === 'no' || value === 'unsure') setAnswer(value); } catch {}
 navigator.geolocation?.getCurrentPosition(p => setCoords({latitude:p.coords.latitude,longitude:p.coords.longitude}),() => {},{timeout:8000,maximumAge:60000}); },[]);
 useEffect(() => { if (!answer) return; let active = true; const local = protocolForTriage(answer); setProtocol(local); setSaved(true);
 getProtocol(local.scenario_id).then(result => { if (active && result.ok) { setProtocol(result.data); setSaved(false); } }); return () => { active = false; }; },[answer]);
 function select(value: TriageAnswer) { setAnswer(value); setProtocol(protocolForTriage(value)); setSaved(true); try { sessionStorage.setItem('rakshak:triage',value); } catch {} }
 return <><BrandHeader /><div className="intro emergency-intro"><p className="eyebrow">The first minutes matter</p><h1>Stay calm.<br /><em>Start here.</em></h1><p className="muted">You can make a difference. One step at a time.</p></div><a className="reassurance" href="#rights"><Icon name="shield" size={21}/><div>Helping someone is a good thing.<span>Know your Good Samaritan rights <span aria-hidden="true">↗</span></span></div></a><CallButtons coords={coords}/><TriageQuestion value={answer} onAnswer={select}/>{protocol ? <StepCards protocol={protocol} offline={saved}/> : <p className="empty-note">Choose an answer to see the next steps.</p>}<div className="two-col more-help"><button onClick={() => setResources(!resources)} aria-expanded={resources}><Icon name="hospital" size={20}/> Trauma centres {resources ? '−' : '+'}</button><a className="button" href="#rights"><Icon name="shield" size={20}/> Your rights</a></div>{resources && <ResourceList type="hospital" coords={coords ? {lat:coords.latitude,lon:coords.longitude} : undefined}/>}<details className="card" id="rights"><summary>Your Good Samaritan rights</summary><ul>{GOOD_SAMARITAN_POINTS.map(point => <li key={point}>{point}</li>)}</ul><p className="caption">General reference information. Contact local authorities for help with a specific situation.</p></details><AskBar mode="emergency" context={{scenario:protocol?.scenario_id}}/></>;
}
