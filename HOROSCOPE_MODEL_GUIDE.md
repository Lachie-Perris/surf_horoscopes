# Surf horoscope model guide

## Recommended first version

The current generator requires no model and therefore no training data. The numerical
interpretation and prose fragments both run locally in `surf_horoscope.py`. Improve
the sign voices and sentence libraries using reviewed examples before considering any
language model.

## Data worth collecting

Create a reviewed evaluation set, ideally as JSONL or a spreadsheet, with:

- spot, timestamp, Hs, primary period, wave direction, wind speed/direction;
- the deterministic wind-quality and ocean-feeling labels;
- sign and desired horoscope;
- editor rating for physical accuracy, spot specificity, sign distinctness, tone,
  usefulness, repetition, and unsupported claims;
- editor corrections and a pass/fail decision.

Cover boundary cases deliberately: tiny and large seas, short and long periods, calm
wind, favourable/unfavourable wind, and directions immediately either side of each
spot's favourable-sector boundary. Start with roughly 50–100 reviewed condition/sign
examples for prompt and evaluation work. Keep a held-out test set that is never used as
a prompt example.

Fine-tuning becomes worthwhile only after the desired editorial voice is stable and
you have several hundred high-quality, consistently edited examples. Fine-tuning is
for tone and format consistency—not for teaching forecast physics. The model should
always receive current numerical conditions and deterministic quality labels.
