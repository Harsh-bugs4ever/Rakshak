'use client';
import { useEffect, useState } from 'react';
import { searchResources } from '@/lib/api';
import { BUNDLED_RESOURCES } from '@/lib/bundled';
import type { Resource, ResourceType } from '@/lib/types';
export interface ResourceListProps { type?: ResourceType; state?: string; city?: string; coords?: { lat: number; lon: number }; onSelect?: (resource: Resource) => void }
export default function ResourceList({ type, state = '', city = '', coords, onSelect }: ResourceListProps) {
 const [kind,setKind] = useState<ResourceType | ''>(type ?? ''); const [region,setRegion] = useState(state); const [town,setTown] = useState(city); const [items,setItems] = useState<Resource[]>([]); const [saved,setSaved] = useState(true);
 const lat = coords?.lat; const lon = coords?.lon;
 useEffect(() => { let active = true;
 const local = BUNDLED_RESOURCES.filter(r => (!kind || r.type === kind) && (!region || r.state.toLowerCase().includes(region.toLowerCase()) || r.state === 'All India') && (!town || r.city.toLowerCase().includes(town.toLowerCase()) || r.state === 'All India'));
 setItems(local); setSaved(true);
 const timer = setTimeout(async () => { const result = await searchResources({type:kind || undefined,state:region,city:town,lat,lon}); if (active && result.ok) { setItems(result.data.items); setSaved(false); } },250);
 return () => { active = false; clearTimeout(timer); }; },[kind,region,town,lat,lon]);
 return <section id="resources"><p className="eyebrow">People who can help</p><h2>{type === 'hospital' ? 'Trauma centres' : 'Support & resources'}</h2><div className="filters">{!type && <label>Type<select value={kind} onChange={e => setKind(e.target.value as ResourceType | '')}><option value="">All resources</option><option value="hospital">Hospitals</option><option value="legal_aid">Legal aid</option><option value="ngo">NGOs</option><option value="scheme">Schemes</option></select></label>}<label>State<input value={region} placeholder="Any state" onChange={e => setRegion(e.target.value)} /></label><label>City<input value={town} placeholder="Any city" onChange={e => setTown(e.target.value)} /></label></div><p className="caption">{saved ? 'Saved sample directory. Verify availability before travelling.' : 'Directory results. Call to confirm availability.'}{lat === undefined && ' Enter your city to find relevant centres.'}</p>{items.map(r => <article className="card resource" key={r.resource_id}><span className="chip">{r.type.replaceAll('_',' ')}</span><h3>{r.name}</h3><p className="caption">{[r.city,r.state].filter(Boolean).join(', ')}{r.distance_km != null && ' · '+r.distance_km.toFixed(1)+' km'}</p><p>{r.description}</p><p className="caption">{r.address}</p><div className="resource-links">{r.contact.phone && <a href={'tel:'+r.contact.phone}>Call {r.contact.phone}</a>}{r.contact.website && <a href={r.contact.website} target="_blank" rel="noreferrer" onClick={() => onSelect?.(r)}>Website ↗</a>}</div></article>)}{!items.length && <p role="status">No matching resources. Try a nearby city or clear the filters.</p>}</section>;
}
