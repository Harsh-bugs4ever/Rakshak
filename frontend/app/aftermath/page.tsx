'use client';
import { useEffect, useState } from 'react';
import BrandHeader from '@/components/shared/BrandHeader';
import Icon from '@/components/shared/Icon';
import StageCard from '@/components/aftermath/StageCard';
import FaqSearch from '@/components/aftermath/FaqSearch';
import ResourceList from '@/components/aftermath/ResourceList';
import AskBar from '@/components/shared/AskBar';
import { listStages } from '@/lib/api';
import { BUNDLED_STAGES } from '@/lib/bundled';
export default function AftermathPage() {
 const [stages,setStages] = useState(BUNDLED_STAGES); const [saved,setSaved] = useState(true);
 useEffect(() => { let active = true; listStages().then(result => { if (active && result.ok && result.data.items.length) { setStages(result.data.items); setSaved(false); } }); return () => { active = false; }; },[]);
 return <><BrandHeader /><div className="intro"><p className="eyebrow">The long road after</p><h1>One step forward.<br /><em>Together.</em></h1><p className="muted">Hospital, paperwork, and support for your family. You do not have to remember it all.</p></div><div className="reassurance"><Icon name="check" size={20}/><div>A little less to remember.<span>Your progress is saved on this device.</span></div></div><section><p className="eyebrow">Your next steps</p><h2>Let’s take it one step at a time</h2><p className="caption">{saved ? 'Showing saved checklists.' : 'Checklists updated from the reference library.'}</p>{[...stages].sort((a,b) => a.order-b.order).map((stage,i) => <StageCard key={stage.stage_id} stage={stage} defaultOpen={i === 0}/>)}</section><FaqSearch/><ResourceList/><AskBar mode="aftermath"/></>;
}
