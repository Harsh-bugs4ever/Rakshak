'use client';
import type { TriageAnswer } from '@/lib/types';
export interface TriageQuestionProps { value?: TriageAnswer; onAnswer: (answer: TriageAnswer) => void }
export default function TriageQuestion({ value, onAnswer }: TriageQuestionProps) {
 return <section><p className="eyebrow">01 / Check & respond</p><h2>Is the person breathing?</h2><div className="triage">{(['yes','no','unsure'] as const).map(answer => <button key={answer} aria-pressed={value === answer} onClick={() => { onAnswer(answer); navigator.vibrate?.(15); }}>{answer === 'yes' ? 'Yes' : answer === 'no' ? 'No' : 'Not sure'}</button>)}</div></section>;
}
