import { redirect } from 'next/navigation';

/**
 * The app always opens on Emergency.
 *
 * A home screen that asks "what do you need?" costs a tap and a decision at the
 * exact moment the user has neither to spare. Families in the aftermath can
 * afford the extra tap; a bystander at a crash scene cannot.
 */
export default function Home() {
  redirect('/emergency');
}
