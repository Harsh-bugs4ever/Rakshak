'use client';
import { useState } from 'react';
import { askEmergency, askAftermath } from '@/lib/api';
import type { EmergencyAiReply, AftermathAiReply } from '@/lib/types';

export interface AskBarProps {
  mode: 'emergency' | 'aftermath';
  context?: Record<string, unknown>;
}

export default function AskBar({ mode, context }: AskBarProps) {
  const [message, setMessage] = useState('');
  const [reply, setReply] = useState<EmergencyAiReply | AftermathAiReply>();
  const [error, setError] = useState('');
  const [source, setSource] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || busy) return;
    setBusy(true);
    setReply(undefined);
    setError('');
    try {
      const result = await (mode === 'emergency'
        ? askEmergency(message, context)
        : askAftermath(message, context));
      if (result.ok) {
        setReply(result.data);
        setSource(result.meta.source);
      } else {
        setError(mode === 'emergency'
          ? 'The assistant is unavailable. Call 112 for immediate help and follow the step cards above.'
          : 'The assistant is unavailable. Use the reference answers and checklists above, or contact a listed support service.');
      }
    } finally {
      setBusy(false);
    }
  }

  return <section className="ask card">
    <span className="eyebrow">A little more guidance</span>
    <h2>Ask a question</h2>
    <form onSubmit={submit}>
      <label className="sr-only" htmlFor={'ask-' + mode}>Your question</label>
      <input id={'ask-' + mode} value={message} onChange={e => setMessage(e.target.value)} maxLength={1000}
        placeholder={mode === 'emergency' ? 'What do I do next?' : 'What documents should I collect?'} required />
      <button disabled={busy || !message.trim()} type="submit">{busy ? 'Asking…' : 'Ask →'}</button>
    </form>
    <div aria-live="polite" aria-busy={busy}>
      {error && <p>{error}</p>}
      {reply && <>
        <p className="caption">{source === 'strands+reference' ? 'Matched with the local assistant · reference answer' : 'Reference guidance'}</p>
        <p className="assistant-copy">{reply.reply}</p>
        {'steps' in reply && reply.steps.length > 0 && <ol>{reply.steps.map(step => <li key={step}>{step}</li>)}</ol>}
        {'do_not' in reply && reply.do_not && reply.do_not.length > 0 && <aside className="warning"><strong>Things to avoid</strong><ul>{reply.do_not.map(item => <li key={item}>{item}</li>)}</ul></aside>}
        {'actions' in reply && reply.actions.some(a => a.type === 'call') && <a className="button" href="tel:112">Call 112</a>}
        {'citations' in reply && reply.citations.length > 0 && <div className="caption"><strong>Reference used</strong><ul>{reply.citations.map(c => <li key={c.faq_id ?? c.stage_id}>{c.question ?? c.title}</li>)}</ul></div>}
        <p className="caption">{reply.disclaimer}</p>
      </>}
    </div>
  </section>;
}
