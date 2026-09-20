"""Grounded assistant responses with optional local model selection.

The visible answer is always copied from a retrieved reference record. A model
can select a FAQ, but cannot introduce a dosage, procedure, contact or citation.
"""
import re

from . import aftermath_agent, emergency_agent, model
from .tools import get_emergency_protocol, get_good_samaritan_info, get_aftermath_steps, search_faqs


def emergency(message, context):
    text = message.lower().replace('’', "'")
    if 'good samaritan' in text or 'my rights' in text:
        info = get_good_samaritan_info()
        return emergency_agent.format_reply({}, '\n'.join(info['points'])), 'reference'

    # Explicit critical language takes priority over a previously selected answer.
    scenario = None
    if re.search(r"not breathing|no breath|isn't breathing|is not breathing|unsure.*breath|not sure.*breath", text):
        scenario = 'not_breathing'
    elif re.search(r'heavy bleeding|bleeding heavily|severe bleeding', text):
        scenario = 'heavy_bleeding'
    elif re.search(r'unconscious (?:but|and|and still) breathing', text):
        scenario = 'unconscious_breathing'
    elif re.search(r'(?:is|still) breathing', text):
        scenario = 'breathing_injured'
    elif re.search(r'next|steps|what now', text):
        value = context.get('scenario')
        if isinstance(value, str) and value in ('not_breathing', 'heavy_bleeding', 'unconscious_breathing', 'breathing_injured'):
            scenario = value

    if scenario:
        protocol = get_emergency_protocol(scenario)
        if protocol.get('found'):
            return emergency_agent.format_reply(protocol, protocol['title']), 'reference'
    return emergency_agent.format_reply({}, 'Call 112 for immediate help. Use the breathing question above to choose the reference steps. If you are unsure, select Not sure.'), 'reference'


def aftermath(message, context):
    faqs = search_faqs(message, limit=3)
    source = 'reference'
    chosen = faqs[:1]
    if faqs and model.enabled():
        try:
            selected = model.select_record(aftermath_agent.build_agent, message, [
                {'record_id': faq['faq_id'], 'question': faq['question'], 'answer': faq['answer']}
                for faq in faqs
            ])
            # Never trust a fabricated ID or expose model prose.
            chosen = [faq for faq in faqs if faq['faq_id'] == selected]
            source = 'strands+reference'
        except Exception:
            source = 'reference-fallback'
    if chosen:
        faq = chosen[0]
        return aftermath_agent.format_reply(faq['answer'], faqs=chosen), source

    stage_id = context.get('stage')
    if isinstance(stage_id, str) and stage_id in ('hospital', 'police', 'insurance', 'legal') and re.search(r'next|steps|checklist', message.lower()):
        stage = get_aftermath_steps(stage_id)
        if stage.get('found'):
            return aftermath_agent.format_reply('\n'.join(stage['checklist']), stage=stage), source
    return aftermath_agent.format_reply('I could not find a reference answer for that question. Try a specific topic such as FIR, insurance or legal aid, or contact a listed support service.'), source
