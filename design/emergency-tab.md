# Emergency Tab — Mobile UI Spec

The user is standing at a crash scene. They are shaking, holding the phone in one
hand, possibly in sunlight, possibly at night. Every design decision below follows
from that.

## The five rules

1. **One decision per screen height.** The fold shows the calls and nothing else
   competing.
2. **Thumb zone only.** Primary actions sit in the bottom two-thirds. Nothing
   critical in the top corners.
3. **Red is rationed.** Only "Call Ambulance" is red. If everything is urgent,
   nothing is.
4. **Read it in 2 seconds.** Max 7 words per button, max 12 per step. No
   paragraphs anywhere on this tab.
5. **No dead ends.** Every state has a visible next action.

## Layout, top to bottom

```
┌─────────────────────────────┐
│ Rakshak          [EN | हिं] │  44px — brand + language, muted
├─────────────────────────────┤
│  You are protected as a     │  Reassurance strip, amber tint
│  Good Samaritan.        (i) │  Tappable → rights sheet
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │  🚑  Call Ambulance   │  │  72px, RED, largest thing on screen
│  │      108 / 112        │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │  🚔  Call Police  112 │  │  64px, dark navy outline
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │  📍  Share Location   │  │  64px, dark navy outline
│  └───────────────────────┘  │
│                             │
├─────────────────────────────┤
│  While you wait             │
│  Is the person breathing?   │  22px semibold
│  ┌──────┐┌──────┐┌───────┐ │
│  │ Yes  ││  No  ││Not sure│ │  56px segmented, equal thirds
│  └──────┘└──────┘└───────┘ │
├─────────────────────────────┤
│  ① Tap their shoulder and   │  Step cards appear only after
│    shout. Do they respond?  │  an answer. Numbered, one line
│  ② Call 112 now. Speaker on.│  of instruction each.
│  ③ Push hard and fast in    │
│    the centre of the chest. │
│                             │
│  ✕ Do not give water        │  Do-nots in a separate red-
│  ✕ Do not move the neck     │  tinted block, never mixed in
├─────────────────────────────┤
│  🏥 Nearest trauma centres  │  Secondary links, plain rows
│  ⚖ Your rights as a helper  │
├─────────────────────────────┤
│  [ Ask a question      🎤 ] │  Sticky above tab bar
├─────────────────────────────┤
│   ● Emergency  │  Aftermath │  56px tab bar, Emergency default
└─────────────────────────────┘
```

## Sizing

| Element | Size | Why |
|---|---|---|
| Ambulance button | 72px tall, 24px bold label | Hit target for a shaking thumb |
| Police / Share | 64px tall, 20px semibold | Important, not primary |
| Triage answers | 56px tall, equal thirds, 12px gap | Fitts's law: no mis-taps |
| Step card text | 18px / 1.45 line height | Readable at arm's length outdoors |
| Min tap target | 48 × 48px | Anything smaller gets missed |
| Side gutter | 16px | Never edge-to-edge text |

## Colour

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--danger` | `#D92B2B` | `#FF5A52` | Ambulance button only |
| `--ink` | `#111827` | `#F2F4F7` | All text |
| `--surface` | `#FFFFFF` | `#14181F` | Cards |
| `--bg` | `#F6F7F9` | `#0B0E13` | Page |
| `--accent` | `#1B3A6B` | `#8FB6F0` | Police / Share outlines |
| `--warn-bg` | `#FFF6E5` | `#2A2113` | Good Samaritan strip |

Contrast target is 7:1 for the step text — phones get used in direct sun.

## Interaction details that matter

- **Calls go straight through.** `<a href="tel:112">` — no confirmation dialog.
  A "are you sure" prompt at a crash scene is a design failure.
- **Share Location** builds the message client-side:
  `whatsapp://send?text=Road accident at https://maps.google.com/?q=<lat>,<lon>. Need ambulance and police.`
  Request geolocation on tab focus, not on tap, so the coordinates are already
  there when they need them. Fall back to `sms:` if WhatsApp is absent.
- **Triage answer persists** in `sessionStorage`. If they lock the phone and come
  back, the steps are still on screen.
- **Steps never collapse.** Once shown, they stay. No accordion.
- **Haptic feedback** (`navigator.vibrate(15)`) on triage selection — confirms
  the tap registered when they are not looking closely.
- **Keep the screen awake** with the Wake Lock API while the Emergency tab is
  active.
- **Offline first.** The four protocols ship in the bundle. The API refreshes
  them; it is never on the critical path.
- **No animations over 150ms.** Nothing that delays information.

## States

| State | What shows |
|---|---|
| Default | Calls + triage question, no steps |
| Answer = No / Not sure | `not_breathing` protocol, severity badge "Critical" |
| Answer = Yes | `breathing_injured` protocol |
| Offline | Bundled protocol + a small "Showing offline guidance" chip |
| Geolocation denied | Share button opens the message without a map link, plus "Type the nearest landmark" |
| AI slow (>2s) | Skeleton steps, never a spinner alone |

## What to deliberately leave out

No onboarding, no login, no splash screen, no carousel, no dark-pattern upsell to
the Aftermath tab. The Emergency tab must be usable by someone who installed the
app 4 seconds ago.

---

A working mockup of all of this is in `design/emergency-mockup.html` — open it in
a phone browser or a 390px-wide DevTools viewport.
