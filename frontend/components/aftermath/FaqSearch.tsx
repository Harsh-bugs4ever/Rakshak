'use client';
import { useEffect, useState } from 'react';
import { searchFaqs } from '@/lib/api';
import { BUNDLED_FAQS } from '@/lib/bundled';
import type { Faq, Topic } from '@/lib/types';
export interface FaqSearchProps { topic?: Topic; onSelect?: (faq: Faq) => void }
export default function FaqSearch({ topic, onSelect }: FaqSearchProps) {
 const [q,setQ] = useState(''); const [items,setItems] = useState(BUNDLED_FAQS); const [saved,setSaved] = useState(true);
 useEffect(() => { let active = true; const timer = setTimeout(async () => {
 const local = BUNDLED_FAQS.filter(f => (!topic || f.topic === topic) && (f.question+' '+f.answer+' '+f.tags?.join(' ')).toLowerCase().includes(q.toLowerCase().trim()));
 setItems(local); setSaved(true);
 const result = await searchFaqs({q,topic}); if (active && result.ok) { setItems(result.data.items); setSaved(false); }
 },250); return () => { active = false; clearTimeout(timer); }; },[q,topic]);
 return <section><label className="field-label" htmlFor="faq-search">Find an answer</label><input id="faq-search" type="search" placeholder="Search FIR, insurance, legal aid…" value={q} onChange={e => setQ(e.target.value)} /><p className="caption">{saved ? 'Saved reference answers' : 'Answers from the reference library'} · {items.length} results</p><div className="faq-results">{items.map(faq => <details className="card" key={faq.faq_id} onToggle={e => { if (e.currentTarget.open) onSelect?.(faq); }}><summary>{faq.question}</summary><span className="chip">{faq.topic.replaceAll('_',' ')}</span><p>{faq.answer}</p></details>)}</div>{!items.length && <p role="status">No matching answer. Try another phrase or contact your District Legal Services Authority.</p>}</section>;
}
