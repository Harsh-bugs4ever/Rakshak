import type { Protocol } from '@/lib/types';
export interface StepCardsProps { protocol: Protocol; offline?: boolean }
export default function StepCards({ protocol, offline }: StepCardsProps) {
 return <section aria-live="polite"><div className="section-heading"><h2>{protocol.title}</h2>{offline && <span className="chip">Saved guidance</span>}</div><p className="muted">{protocol.subtitle}</p><ol className="steps">{protocol.steps.map(step => <li key={step}>{step}</li>)}</ol><aside className="warning"><strong>Things to avoid</strong><ul>{protocol.do_not.map(item => <li key={item}>{item}</li>)}</ul></aside></section>;
}
