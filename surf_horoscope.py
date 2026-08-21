"""Lightweight, offline surf-horoscope generator with no API or model."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

STAR_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
              "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")

SIGN_VOICES = {
    "Aries": ("decisive energy", "Let commitment begin after observation, not before it.",
              ("choose one peak and commit", "pause for two sets before moving")),
    "Taurus": ("patient rhythm", "Quality will matter more than wave count today.",
               ("settle into the rhythm", "wait for the wave with real shape")),
    "Gemini": ("quick adaptability", "Read changing peaks without scattering your attention.",
               ("adjust once, then trust the choice", "watch how the peak shifts")),
    "Cancer": ("strong intuition", "Sensitivity is useful when it becomes careful observation.",
               ("trust the pattern you notice", "take a quiet shoreline read")),
    "Leo": ("warm confidence", "The best line needs presence, not performance.",
            ("surf one wave with generous style", "make space as confidently as you take it")),
    "Virgo": ("precise attention", "Refinement beats perfection when the sea keeps moving.",
              ("refine one part of your take-off", "make positioning the practice")),
    "Libra": ("instinct for balance", "Find the point where effort and ease meet.",
              ("share the peak and preserve your rhythm", "choose the cleanest balanced line")),
    "Scorpio": ("calm intensity", "Meet the ocean's force without trying to overpower it.",
                ("commit fully to a carefully chosen wave", "keep your breathing steady")),
    "Sagittarius": ("adventurous perspective", "Exploration works best when respect sets the boundary.",
                    ("explore a different bank after watching it", "leave room for an unexpected line")),
    "Capricorn": ("disciplined patience", "Positioning and persistence will outperform urgency.",
                  ("build the session one sound decision at a time", "hold the patient position")),
    "Aquarius": ("independent imagination", "Try the unusual line after understanding the ordinary one.",
                 ("experiment with one fresh line", "look beyond the obvious peak")),
    "Pisces": ("deep sensitivity", "Tune into the sea without drifting away from the facts.",
               ("follow the ocean's tempo", "turn feeling into a deliberate line")),
}

# Wind directions are FROM, clockwise from north.
SPOT_RULES = {
    "Bondi Beach": {"sectors": ((270.0, 360.0), (0.0, 0.0)), "label": "W to N"},
    "Byron Bay": {"sectors": ((135.0, 225.0),), "label": "SW to SE via S"},
}

LOCATION_OPENINGS = {
    "Bondi Beach": (
        "The eastern edge is carrying a {mood} mood today.",
        "The ocean arrives with a {mood} but unmistakable presence.",
        "The water feels {mood}, asking the city to match its tempo.",
        "The day wakes to an ocean with a distinctly {mood} character.",
    ),
    "Byron Bay": (
        "Around the headland, the sea settles into a {mood} rhythm.",
        "The open horizon holds a {mood} ocean today.",
        "The water carries a {mood} energy around the bay.",
        "The sea feels {mood}, moving to its own spacious tempo.",
    ),
}
FEELING_LINES = (
    "Its character is {height_feel}, while the rhythm underneath is {energy}.",
    "On the surface it feels {height_feel}; beneath that, the pulse is {energy}.",
    "The ocean's body is {height_feel}, carried by energy that is {energy}.",
    "Expect water that feels {height_feel}, with a rhythm that remains {energy}.",
)
WIND_LINES = {
    "light": (
        "A light {wind_dir} breath leaves the surface largely untouched.",
        "The breeze is quiet enough for the ocean's natural shape to show through.",
        "Little wind interferes, so the water keeps an open, unforced face.",),
    "clean": (
        "The {wind_dir} wind is grooming the surface into cleaner lines.",
        "A tidy {wind_dir} breeze gives the ocean a more polished face.",
        "The wind is helping the sea organise itself into clean, readable lines.",),
    "messy": (
        "The {wind_dir} wind is roughening the surface and breaking up the lines.",
        "Wind texture makes the ocean feel scattered, so patience will reveal the better moments.",
        "The surface is untidy under the {wind_dir} wind, with shape hiding inside the noise.",),
}
HEADLINE_PATTERNS = {
    "Aries": "Commit to {subject}", "Taurus": "Wait for {subject}",
    "Gemini": "Read {subject}", "Cancer": "Trust {subject}",
    "Leo": "Meet {subject} with Presence", "Virgo": "Find Precision in {subject}",
    "Libra": "Balance Within {subject}", "Scorpio": "Go Deeper into {subject}",
    "Sagittarius": "Explore {subject}", "Capricorn": "Build Around {subject}",
    "Aquarius": "Reimagine {subject}", "Pisces": "Feel {subject}",
}
HEADLINE_SUBJECTS = {
    "Bondi Beach": {
        "light": ("the Open {mood} Face", "the {mood} Eastern Pulse"),
        "clean": ("the Clean {mood} Pulse", "the Groomed {mood} Lines"),
        "messy": ("Shape in the {mood} Static", "the Restless {mood} Edge"),
    },
    "Byron Bay": {
        "light": ("the Open {mood} Rhythm", "the {mood} Headland Pulse"),
        "clean": ("the Clean {mood} Rhythm", "the Groomed {mood} Headland Lines"),
        "messy": ("Shape in the {mood} Texture", "the Restless {mood} Headland Water"),
    },
}


@dataclass
class Horoscope:
    sign: str
    headline: str
    reading: str
    surf_intention: str


@dataclass
class SpotHoroscopes:
    location: str
    conditions_summary: str
    horoscopes: list[Horoscope]

    def model_dump_json(self, indent=2):
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False)


def compass_direction(degrees):
    points = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
    return points[int((degrees % 360 + 11.25) // 22.5) % 16]


def _in_sector(direction, start, end):
    direction %= 360
    if start == end == 0:
        return direction == 0
    return start <= direction <= end if start <= end else direction >= start or direction <= end


def interpret_conditions(row):
    """Turn forecast values into explicit, auditable writing facts."""
    location = str(row["location"])
    if location not in SPOT_RULES:
        raise KeyError(f"No wind rule configured for {location!r}")
    hs, period = float(row["wave_height_m"]), float(row["primary_period_s"])
    wind_speed = float(row["wind_speed_m_s"])
    wind_direction = float(row["wind_direction_deg"]) % 360
    wave_direction = float(row.get("primary_direction_deg", float("nan")))

    if hs < 0.5:
        mood, height_feel = "quiet", "sleepy and delicate, with scarce push"
    elif hs < 1.0:
        mood, height_feel = "playful", "small and playful, rewarding timing more than force"
    elif hs < 1.8:
        mood, height_feel = "lively", "approachable but energetic enough for committed surfing"
    elif hs < 2.8:
        mood, height_feel = "powerful", "powerful and demanding, with a serious pulse"
    else:
        mood, height_feel = "imposing", "heavy and imposing, with consequence in every decision"

    if period < 8:
        period_feel = "short-period and restless, with closely packed energy"
    elif period < 11:
        period_feel = "moderately organised but active and peaky"
    elif period < 14:
        period_feel = "cleanly pulsing, with readable lines and breathing room"
    else:
        period_feel = "deep and deliberate, carrying long-period energy beneath the surface"

    favourable = any(_in_sector(wind_direction, a, b) for a, b in SPOT_RULES[location]["sectors"])
    if wind_speed < 2.0:
        wind_quality, wind_feel = "light", "open-faced and barely textured by wind"
    elif favourable:
        wind_quality, wind_feel = "clean", "cleaner and more organised under the local wind"
    else:
        wind_quality, wind_feel = "messy", "messy and broken up by the local wind"

    return {
        "location": location, "valid_time_utc": str(pd.Timestamp(row["valid_time_utc"])),
        "wave_height_m": round(hs, 2), "primary_period_s": round(period, 1),
        "wave_direction": None if pd.isna(wave_direction) else compass_direction(wave_direction),
        "wind_speed_m_s": round(wind_speed, 1), "wind_direction": compass_direction(wind_direction),
        "wind_direction_deg": round(wind_direction), "wind_quality": wind_quality,
        "clean_wind_rule": SPOT_RULES[location]["label"], "ocean_mood": mood,
        "height_feel": height_feel, "period_feel": period_feel,
        "ocean_feeling": f"{height_feel}; {period_feel}; {wind_feel}",
    }


def current_rows(forecast):
    """Return the forecast row closest to now for each location."""
    data = forecast.copy()
    data["valid_time_utc"] = pd.to_datetime(data["valid_time_utc"], utc=True)
    data["distance_from_now"] = (data["valid_time_utc"] - pd.Timestamp.now(tz="UTC")).abs()
    return data.loc[data.groupby("location")["distance_from_now"].idxmin()].drop(columns="distance_from_now")


def _rng(conditions, sign):
    day = pd.Timestamp(conditions["valid_time_utc"]).strftime("%Y-%m-%d")
    digest = hashlib.sha256(f"{day}|{conditions['location']}|{sign}|v1".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def generate_spot_horoscopes(conditions):
    """Create all 12 readings locally from curated components."""
    summary = (f"Wave height {conditions['wave_height_m']:.1f} m with a "
               f"{conditions['primary_period_s']:.0f}-second primary rhythm. "
               f"The {conditions['wind_direction']} wind leaves the surface "
               f"{conditions['wind_quality']}. Overall, the ocean feels "
               f"{conditions['ocean_feeling']}.")
    values = {"location": conditions["location"], "mood": conditions["ocean_mood"],
              "hs": conditions["wave_height_m"], "period": conditions["primary_period_s"],
              "height_feel": conditions["height_feel"], "energy": conditions["period_feel"],
              "wind_dir": conditions["wind_direction"],
              "wind_speed": conditions["wind_speed_m_s"]}
    reports = []
    for sign in STAR_SIGNS:
        rng = _rng(conditions, sign)
        gift, lesson, actions = SIGN_VOICES[sign]
        reading = " ".join((rng.choice(LOCATION_OPENINGS[conditions["location"]]).format(**values),
                            rng.choice(FEELING_LINES).format(**values),
                            rng.choice(WIND_LINES[conditions["wind_quality"]]).format(**values),
                            f"Your {gift} is useful here. {lesson}"))
        subject = rng.choice(
            HEADLINE_SUBJECTS[conditions["location"]][conditions["wind_quality"]]
        ).format(mood=conditions["ocean_mood"].title())
        headline = HEADLINE_PATTERNS[sign].format(subject=subject)
        reports.append(Horoscope(sign, headline, reading,
                                 rng.choice(actions).capitalize() + "."))
    return SpotHoroscopes(conditions["location"], summary, reports)


def _as_markdown(report, conditions):
    lines = [f"# {report.location} surf horoscopes", "",
             f"*Conditions valid {conditions['valid_time_utc']}*", "", report.conditions_summary, ""]
    for item in report.horoscopes:
        lines += [f"## {item.sign} — {item.headline}", "", item.reading, "",
                  f"**Surf intention:** {item.surf_intention}", ""]
    return "\n".join(lines)


def generate_all_horoscopes(forecast, output_dir="output"):
    """Generate and save both reports, fully offline."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    for _, row in current_rows(forecast).iterrows():
        conditions = interpret_conditions(row)
        report = generate_spot_horoscopes(conditions)
        reports[report.location] = report
        slug = report.location.lower().replace(" beach", "").replace(" ", "_")
        (output_dir / f"surf_horoscopes_{slug}.json").write_text(report.model_dump_json(), encoding="utf-8")
        (output_dir / f"surf_horoscopes_{slug}.md").write_text(_as_markdown(report, conditions), encoding="utf-8")
    metadata = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "generator": "offline curated templates v1", "locations": list(reports)}
    (output_dir / "surf_horoscope_run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return reports
