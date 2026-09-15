# Surf horoscope model guide

## Recommended first version

The current generator requires no model and therefore no training data. The numerical
interpretation and prose fragments both run locally in `surf_horoscope.py`. Improve
the sign voices and sentence libraries using reviewed examples before considering any
language model.

## Data worth collecting

Create a reviewed evaluation set, ideally as JSONL or a spreadsheet, with:

- spot, timestamp, wave height, primary period, wave direction, wind speed/direction;
- tide height, rising/falling/turning state, next high/low time, reference station,
  and whether the height is predicted, observed or interpolated;
- the deterministic wind-quality and ocean-feeling labels;
- sign and desired horoscope;
- editor rating for physical accuracy, spot specificity, sign distinctness, tone,
  usefulness, repetition, and unsupported claims;
- editor corrections and a pass/fail decision.

Cover boundary cases deliberately: tiny and large seas, short and long periods, calm
wind, clean/messy wind, and directions immediately either side of each
spot's clean-wind sector boundary. Include rising, falling, high and low tide examples,
and several tidal ranges. Start with roughly 50–100 reviewed condition/sign
examples for prompt and evaluation work. Keep a held-out test set that is never used as
a prompt example.

Fine-tuning becomes worthwhile only after the desired editorial voice is stable and
you have several hundred high-quality, consistently edited examples. Fine-tuning is
for tone and format consistency—not for teaching forecast physics. The model should
always receive current numerical conditions and deterministic quality labels.

## Tide writing rules

Treat the tide as physical forecast context first and astrological imagery second.

- Keep the rising, falling, near-high or near-low state in the structured conditions.
  Mention it in prose when it changes the ocean's felt character; add the next turn
  only when useful. Never invent a preferred tide for a beach without reviewed local
  evidence.
- Describe feeling as gathering/filling on a rising tide, releasing/opening on a
  falling tide, full/held near high water, and exposed/revealing near low water.
- The Moon and Sun physically drive astronomical tides. Star signs and horoscope
  meanings do not. The report may use the visible tidal rhythm as a poetic bridge to
  the lunar horoscope, but must not present astrology as a cause of local tide height.
- Never describe an interpolated prediction as a live observation. Keep the reference
  port and data provenance in the structured conditions even when the prose is spare.
- Tide does not make unsafe surf safe. Avoid navigation, swimming-safety or exact
  breaking-wave claims.

## Output structure

Each star sign must receive one headline and one continuous paragraph. The paragraph
should weave the sky, physical tide, surface quality and swell rhythm into a single
description of how the ocean may feel to that sign. Do not render a separate cosmic
summary, surf report, tip, mantra or blockquote. Avoid listing forecast inputs in prose;
translate them into felt qualities and let the sign-specific advice arise from the same
ocean moment.

## Editorial voice and selection

The deterministic forecast and astrology context are inputs, not a checklist to recite.
Select the two or three details that most strongly define this spot's conditions and
this sign's response. Wind-affected surface, swell rhythm and tide may be enough; the
wave height, period, Moon sign and planetary aspect can remain in the data panel. Do
not force every available value into the paragraph. Never omit a material hazard or
turn an uncertain offshore model value into a confident beach-level claim.

Write like a person observing the sea, not like a schema being read aloud. Prefer one
concrete observation—shifting peaks, closely spaced lines, surface chop, a falling
tide revealing more shoreline—to several abstract labels. Mix short and longer
sentences. Avoid symmetrical stacks of adjectives such as “quick, closely packed lines
beneath a scattered, wind-ruffled face.” Read the paragraph aloud during review.

The horoscope should alter how the sea is *experienced*, not arrive after a standalone
surf report. Give the sign a specific tension or opportunity caused by the current
conditions. For example, Gemini's curiosity could help identify a shifting peak but
could also lead to moving too often in a messy lineup. Advice should follow from that
tension rather than from a fixed generic trait.

Use astrology to choose tone and attention where possible, rather than naming each
placement. A Mercury–Uranus cue might suggest curiosity or inventiveness; Moon in
Scorpio might suggest perceptiveness; Saturn might suggest restraint. Name at most
one placement or aspect if it contributes a clear image. These are imaginative
associations, not physical forecast causes or factual claims about a person's life.

If a third-party daily tip is used, paraphrase its useful idea and connect it to the
same ocean moment. Do not append a lengthy verbatim tip or introduce it with “Let
that lesson travel beyond the water.” The transition to life beyond surfing should
feel implicit. The paragraph must still stand on its own if the astrology service is
unavailable.

## Narrative variation

Rotate among genuinely different story shapes; changing only the opening sentence
does not create a new composition:

- Ocean first → what this sign notices → a restrained choice.
- Sign first → how the conditions challenge that trait → a concrete session image.
- Physical image first → a subtle lunar or planetary echo → practical guidance.
- Direct forecast voice → a brief horoscope turn → a quiet closing thought.

Keep Bondi and Byron distinct through their own wind rules and coastal character,
without announcing the spot name inside a report whose location is already visible.

## Review checks

- Aim for roughly 70–100 words; vary length when the conditions call for it.
- One headline and one paragraph, with no separate mantra or cosmic explanation.
- No more than one explicitly named astrological placement or aspect.
- No more than one semicolon; preferably none.
- At least one concrete ocean observation and one sign-specific response to it.
- Prefer “clean,” “tidy,” “roughened” or “messy” to “favourable” or “unfavourable.”
- Avoid “colouring your outlook,” “particular current,” “that lesson,” “beyond the
  water,” and other phrases that merely announce a template transition.
- Do not repeat the sign or spot name when the page already labels them, unless a
  sentence genuinely needs it.
- Check the same sign across both spots and all twelve signs at one spot for repeated
  sentence structures, unsupported claims and practical usefulness.

### Example: Gemini, messy short-period surf and a falling tide

> The ocean is restless today, with short lines arriving close together and the
> northerly wind breaking up their shape. As the tide falls, more of the shoreline
> opens up, but the better waves may appear briefly and in unexpected places. Your
> instinct will be to keep searching; give one bank enough time to reveal itself
> before moving on. Watch for the pattern hiding beneath the surface noise—asking a
> better question may also shift something that has felt stuck away from the water.

This illustrates editorial selection and flow, not an exact beach-level prediction.
An actual generated reading must be checked against its current structured conditions.
