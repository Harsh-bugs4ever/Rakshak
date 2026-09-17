"""
Rakshak - Build Guide PDF generator.

Usage:
    pip install fpdf2
    python tools/make_pdf.py                 # writes Rakshak_Build_Guide.pdf
    python tools/make_pdf.py out/guide.pdf   # custom output path

Works with fpdf2. Because the built-in Helvetica font is latin-1 only, all text
is normalised through clean() first - otherwise the en-dashes and curly quotes
in the guide raise UnicodeEncodeError at render time.
"""

import os
import sys

from fpdf import FPDF

# --- unicode -> latin-1 safe -------------------------------------------------

REPLACEMENTS = {
    "–": "-", "—": "-",          # en / em dash
    "‘": "'", "’": "'",          # curly single quotes
    "“": '"', "”": '"',          # curly double quotes
    "…": "...", "•": "-",        # ellipsis, bullet
    " ": " ", "→": "->",         # nbsp, arrow
    "₹": "Rs.",                       # rupee sign
}


def clean(text):
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    # Drop anything still outside latin-1 (emoji, Devanagari) rather than crash.
    return text.encode("latin-1", "ignore").decode("latin-1")


# --- document ---------------------------------------------------------------

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, clean("Rakshak - Accident Emergency & Aftermath (Build Guide)"),
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, "Page %d" % self.page_no(), align="C")
        self.set_text_color(0, 0, 0)

    def h1(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(230, 238, 248)
        self.cell(0, 9, clean(" " + text), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h2(self, text):
        self.ln(1)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, clean(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        for line in text.strip("\n").splitlines():
            stripped = line.lstrip()
            if not stripped:
                self.ln(3)
                continue
            indent = 4 if stripped.startswith(("-", "*")) else 0
            self.set_x(self.l_margin + indent)
            self.multi_cell(0, 5.5, clean(stripped), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def code(self, text):
        self.set_font("Courier", "", 8.5)
        self.set_fill_color(245, 245, 245)
        for line in text.strip("\n").splitlines():
            self.multi_cell(0, 4.6, clean(line or " "), fill=True,
                            new_x="LMARGIN", new_y="NEXT")
        self.ln(3)


# --- content ----------------------------------------------------------------
# Each entry: (kind, payload) where kind is "h1" | "h2" | "body" | "code".

CONTENT = [
    ("h1", "1) Vision & Scope"),
    ("body", """
Goal: one app that helps ordinary people in India in two critical moments.
- Immediately after seeing a road accident, as a bystander.
- In the days and weeks after their own family meets with an accident.

Hackathon positioning
- Track: Build It (open-source AWS stack, running locally).
- Also competing for: Best UI.
- Story: "One app, two modes: first minutes matter, and the long road after."

MVP scope (4 days)
- Two main tabs: Emergency (bystander) and Aftermath (family).
- AI assistant (Strands Agents) for first-aid guidance and process FAQs.
- Local serverless backend: SAM + LocalStack, DynamoDB, OpenSearch.
- Cedar policies: anyone reads, only admins write.
- Panic-friendly, mobile-first UI.
"""),

    ("h1", "2) User Journeys"),
    ("h2", "Journey A - 'I just saw an accident' (Emergency tab)"),
    ("body", """
1. App opens on the Emergency tab by default.
2. Three full-width action buttons: Call Ambulance (108/112), Call Police (112),
   Share Location & Info (pre-filled WhatsApp/SMS with a Maps link).
3. Quick triage: "Is the person breathing?" -> Yes / No / Not sure.
   - Not breathing or not sure: check responsiveness, call 112, start chest
     compressions at 100-120/min, continue until help arrives.
   - Breathing: do not move them unless there is fire risk, control bleeding with
     firm pressure, keep them warm and still, no food or water.
4. More help: nearest trauma centres, Good Samaritan rights in plain language.
5. Ask-a-question box backed by EmergencyGuideAgent.

Microcopy that matters
- "You don't need to be a doctor. Just follow these steps."
- "You are protected as a Good Samaritan. You don't have to reveal your identity."
"""),
    ("h2", "Journey B - 'My family met with an accident' (Aftermath tab)"),
    ("body", """
Four stages, each a card with a checklist plus short explanations.

At Hospital
- Ensure the victim is registered as an MLC (Medico-Legal Case).
- Collect admission summary, prescriptions, test reports, every bill.
- Emergency care cannot be denied for lack of payment or police formalities.

At Police Station
- File the FIR at the station nearest the accident spot.
- Check that time, place, vehicles and injuries are recorded correctly.
- Always ask for a copy of the FIR; insist on hit-and-run registration if relevant.

Insurance Claim
- Inform the insurer as early as possible.
- Assemble FIR copy, MLC papers, bills, discharge summary, photographs.
- Hit-and-run cases: the Solatium Fund route via the district administration.

Legal Aid & Compensation
- Motor Accidents Claims Tribunal (MACT) handles compensation claims.
- Free legal aid through State Legal Services Authorities (SLSA).
- Claims can cover medical costs, lost income, disability and death.
"""),

    ("h1", "3) Tech Architecture"),
    ("body", """
- Frontend: React / Next.js, two tabs, mobile-first.
- AI: Strands Agents SDK - EmergencyGuideAgent and AftermathGuideAgent.
- Backend: SAM CLI + LocalStack. API Gateway -> Lambda -> DynamoDB + OpenSearch.
- Tables: EmergencyProtocols, AftermathSteps, Resources, FAQs.
- Search: OpenSearch indexes for resources and aftermath topics.
- Authorization: Cedar policies evaluated inside the Lambda handlers.
"""),

    ("h1", "4) Data Models"),
    ("body", """
EmergencyProtocols  scenario_id, title, steps[], do_not[], tags[]
AftermathSteps      stage_id, title, checklist[], details[], tags[]
Resources           resource_id, name, type, state, city, address, contact,
                    description, tags[]
FAQs                faq_id, question, answer, topic, tags[]
"""),
    ("code", """
{
  "scenario_id": "not_breathing",
  "title": "Person is not breathing",
  "severity": "critical",
  "steps": [
    "Tap the shoulder and shout - check if they respond.",
    "Call 112 now. Put the phone on speaker.",
    "If trained, push hard and fast in the centre of the chest, 100-120/min.",
    "Keep going until they breathe or the ambulance arrives."
  ],
  "do_not": ["Do not give water.", "Do not shake the head or neck."],
  "tags": ["breathing", "cpr", "critical"]
}
"""),

    ("h1", "5) Strands Agents Design"),
    ("body", """
EmergencyGuideAgent tools
- get_emergency_protocol(scenario)
- get_state_emergency_numbers(state)
- get_good_samaritan_info()

AftermathGuideAgent tools
- get_aftermath_steps(stage)
- search_resources(query, state, type)
- answer_aftermath_faq(question)

Keep the emergency agent deterministic: short numbered steps, no speculation,
and always end with "Call 112 if you have not already."
"""),

    ("h1", "6) Backend APIs"),
    ("body", """
GET  /emergency/protocols?scenario=not_breathing
GET  /emergency/good-samaritan
GET  /aftermath/steps?stage=hospital
GET  /aftermath/faqs?topic=fir&q=delay
GET  /resources?type=hospital&state=Karnataka&city=Bengaluru
POST /ai/emergency
POST /ai/aftermath

Full request and response shapes are in docs/api-spec.md; seed payloads for every
table are in data/*.json.
"""),

    ("h1", "7) Cedar Policies"),
    ("code", """
// Anyone may read the public safety content
permit(
  principal,
  action in [Action::"read", Action::"search"],
  resource in Namespace::"PublicContent"
);

// Only admins may change it
permit(
  principal in Role::"admin",
  action in [Action::"write", Action::"delete"],
  resource in Namespace::"PublicContent"
);
"""),

    ("h1", "8) Frontend & Best UI"),
    ("body", """
Global principles
- Mobile-first, 56-72px tall primary buttons, thumb-reachable.
- Panic-friendly: one decision per screen, minimal text, high contrast.
- Calm tone. Short sentences. No jargon without a one-line explanation.
- India-specific: 108/112, MLC, FIR, Good Samaritan, SLSA, MACT.

Emergency tab
- Three stacked action buttons above the fold, then the triage question,
  then step cards revealed by the answer.
- Red is reserved for the ambulance and police actions only - everything else is
  neutral, so the critical action never competes for attention.

Aftermath tab
- Search bar, four stage cards, checklists with persisted checkbox state,
  and a resource list filtered by type, state and city.
"""),

    ("h1", "9) 4-Day Build Plan"),
    ("body", """
Day 1  Content for 4 scenarios, 4 stages, 15 FAQs. SAM + LocalStack up,
       tables created and seeded, first read Lambdas working.
Day 2  Strands agents, /ai endpoints, OpenSearch resource search, Cedar checks.
Day 3  Frontend: two tabs, triage flow, checklists, FAQ search, AI chat wired up.
Day 4  UI polish, sample resources, Good Samaritan screen, 3-minute demo video,
       README and submission write-up.
"""),

    ("h1", "10) What to Emphasize for Judges"),
    ("body", """
- Impact: India's accident crisis, the first minutes, and the months after.
- Stack: Strands Agents, SAM + LocalStack, OpenSearch, Cedar - all open source.
- Learning: first agentic app, first serverless app, first Cedar policies.
- Execution: both journeys work end to end, not just the demo path.
- Demo: show real use, not architecture diagrams. Lead with the crash scene.
"""),
]


def build(out_path):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 15, 18)
    pdf.add_page()

    # Title block
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(0, 14, "Rakshak", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 8, clean("Accident Emergency & Aftermath - Build Guide"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 6, "Build It track  |  Best UI  |  4-day MVP",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.add_page()

    render = {"h1": pdf.h1, "h2": pdf.h2, "body": pdf.body, "code": pdf.code}
    for kind, payload in CONTENT:
        render[kind](payload)

    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    pdf.output(out_path)
    return out_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Rakshak_Build_Guide.pdf"
    print("Wrote", build(target))
