import test from 'node:test';
import assert from 'node:assert/strict';
import { protocolForTriage, shareMessage } from '../lib/offline.ts';

test('No and Not sure both select critical guidance', () => {
  for (const answer of ['no', 'unsure']) {
    const protocol = protocolForTriage(answer);
    assert.equal(protocol.scenario_id, 'not_breathing');
    assert.equal(protocol.severity, 'critical');
    assert.ok(protocol.steps.some(step => step.includes('112')));
  }
});

test('Yes selects the breathing and injured protocol', () => {
  assert.equal(protocolForTriage('yes').scenario_id, 'breathing_injured');
});

test('Sharing without location does not invent a map pin', () => {
  const text = shareMessage();
  assert.ok(text.includes('Need ambulance and police'));
  assert.ok(!text.includes('maps.google.com'));
  assert.ok(!text.includes('undefined'));
});

test('Sharing preserves zero coordinates', () => {
  assert.ok(shareMessage({ latitude: 0, longitude: 0 }).includes('?q=0,0'));
});
