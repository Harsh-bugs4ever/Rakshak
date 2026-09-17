/**
 * Bundled emergency content.
 *
 * These four protocols ship inside the JavaScript bundle. They are never
 * fetched, so they work with no network, no LocalStack and no AWS - which is
 * the state the app is most likely to be in at a roadside at 2am.
 *
 * The API refreshes this content when it is reachable; it is never on the
 * critical path. Keep in sync with data/emergency_protocols.json - the
 * frontend test suite should diff them.
 */

import type { Protocol, TriageAnswer } from './types';

export const OFFLINE_PROTOCOLS: Record<string, Protocol> = {
  not_breathing: {
    scenario_id: 'not_breathing',
    title: 'Person is not breathing',
    severity: 'critical',
    subtitle: 'Every second counts. Do these in order.',
    steps: [
      'Tap their shoulder and shout loudly. Check if they respond.',
      'Call 112 now and put the phone on speaker so your hands are free.',
      'If you are trained: push hard and fast in the centre of the chest, 100-120 per minute.',
      'Do not stop until they start breathing or the ambulance team takes over.',
    ],
    do_not: [
      'Do not give water or food.',
      'Do not shake or twist the head and neck.',
      'Do not leave them alone to go look for help - call instead.',
    ],
  },
  breathing_injured: {
    scenario_id: 'breathing_injured',
    title: 'Person is breathing but injured',
    severity: 'high',
    subtitle: 'Keep them still and stop the bleeding.',
    steps: [
      'Call 112 and say the exact location. Share a map link if you can.',
      'Press a clean cloth firmly on any bleeding wound and keep pressing.',
      'Keep them warm and talking. Loosen tight clothing around the neck.',
      'Stay with them until help arrives.',
    ],
    do_not: [
      'Do not move them unless there is fire, fuel leak or oncoming traffic.',
      'Do not remove a helmet unless they are not breathing.',
      'Do not give food, water or any medicine.',
    ],
  },
  heavy_bleeding: {
    scenario_id: 'heavy_bleeding',
    title: 'Heavy bleeding',
    severity: 'critical',
    subtitle: 'Direct pressure is the single most effective thing you can do.',
    steps: [
      'Press down hard on the wound with a clean cloth, shirt or dupatta.',
      'Do not lift the cloth to check. Add more cloth on top if it soaks through.',
      'If the wound is on an arm or leg, raise it above the level of the heart.',
      'Call 112 and keep pressing until help arrives.',
    ],
    do_not: [
      'Do not wash the wound or pull out any embedded object.',
      'Do not use a tourniquet unless you are trained and the limb is severed.',
    ],
  },
  unconscious_breathing: {
    scenario_id: 'unconscious_breathing',
    title: 'Unconscious but breathing',
    severity: 'high',
    subtitle: 'Protect the airway, do not move the spine.',
    steps: [
      'Call 112 first.',
      'Check that nothing is blocking the mouth.',
      'If there is no sign of neck or back injury, roll them gently onto their side.',
      'Watch their breathing continuously until the ambulance arrives.',
    ],
    do_not: [
      'Do not splash water on the face or slap them awake.',
      'Do not put anything in the mouth.',
      'Do not prop them up in a sitting position.',
    ],
  },
};

/** Numbers, hardcoded. There is no scenario where fetching these is acceptable. */
export const OFFLINE_NUMBERS = {
  ambulance: '108',
  police: '112',
  unified: '112',
  note: '112 works everywhere in India.',
} as const;

export const GOOD_SAMARITAN_POINTS = [
  'You cannot be forced to reveal your name or address.',
  "You cannot be detained or made to pay for the victim's treatment.",
  'Hospitals must start emergency treatment without waiting for police formalities.',
  'If you choose to be a witness, you can be examined only once, at a time and place you pick.',
] as const;

/** Maps the triage answer to the protocol to show. "Not sure" gets the critical path. */
export function protocolForTriage(answer: TriageAnswer): Protocol {
  return answer === 'yes'
    ? OFFLINE_PROTOCOLS.breathing_injured
    : OFFLINE_PROTOCOLS.not_breathing;
}

/** Builds the pre-filled share message; omits the pin if geolocation failed. */
export function shareMessage(coords?: { latitude: number; longitude: number }): string {
  const pin = coords
    ? ` at https://maps.google.com/?q=${coords.latitude},${coords.longitude}`
    : ' nearby';
  return `Road accident${pin}. Need ambulance and police. Please help.`;
}
