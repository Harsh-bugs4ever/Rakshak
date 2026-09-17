'use client';

/**
 * Emergency tab - TODO Day 3.
 *
 * Full spec in design/emergency-tab.md; a working reference implementation of
 * every interaction is in design/emergency-mockup.html. Port that, do not
 * redesign it.
 *
 * Order on screen (never reorder - it is the whole design):
 *   1. Good Samaritan reassurance strip
 *   2. Call Ambulance (72px, red, the only red thing)
 *   3. Call Police / Share Location (64px, navy outline)
 *   4. "Is the person breathing?" -> Yes / No / Not sure
 *   5. Step cards, then Do-nots in a separate red-tinted block
 *   6. Nearest trauma centres / Your rights
 *
 * Behaviour that is easy to miss:
 *   - `tel:` links fire directly, with no confirmation dialog.
 *   - Request geolocation on mount, not on tap, so the pin is ready in advance.
 *   - Persist the triage answer in sessionStorage so locking the phone does not
 *     lose their place.
 *   - Render from OFFLINE_PROTOCOLS first, then reconcile with the API.
 */

import { OFFLINE_PROTOCOLS, protocolForTriage } from '@/lib/offline';

export default function EmergencyPage() {
  return (
    <div>
      <h1>Emergency</h1>
      {/* TODO: <GoodSamaritanStrip /> <CallButtons /> <TriageQuestion /> <StepCards /> */}
      <p>Not built yet - see design/emergency-mockup.html.</p>
    </div>
  );
}

export { OFFLINE_PROTOCOLS, protocolForTriage };
