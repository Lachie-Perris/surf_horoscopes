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

- State whether it is rising, falling, near high or near low, and include the next
  turn when it is useful. Never invent a preferred tide for a beach without reviewed
  local evidence.
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
