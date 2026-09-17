'use client';

/**
 * Aftermath tab - TODO Day 3.
 *
 * Layout:
 *   1. Search bar: "Search topics (FIR, insurance, legal aid...)"
 *   2. Four stage cards in `order`: Hospital, Police, Insurance, Legal
 *      - each expands to a checklist with persisted checkbox state
 *      - plus short explanation paragraphs from `details`
 *   3. Resource list, filterable by type / state / city
 *   4. Ask-a-question box
 *
 * Unlike the Emergency tab, this one may show a loading state - the user is at
 * a desk or in a waiting room, not at a roadside. Prefer completeness over speed
 * here, and never truncate a checklist.
 *
 * Checkbox state belongs in localStorage keyed by stage_id: families work
 * through these over days, across many sessions.
 */

export default function AftermathPage() {
  return (
    <div>
      <h1>Aftermath</h1>
      {/* TODO: <FaqSearch /> <StageCard /> x4 <ResourceList /> <AskBar /> */}
      <p>Not built yet.</p>
    </div>
  );
}
