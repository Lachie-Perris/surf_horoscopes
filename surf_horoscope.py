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

OPENINGS = (
    "The sea is speaking in {mood} tones at {location}.",
    "At {location}, the water carries a {mood} character.",
    "Today's ocean at {location} feels {mood}.",
)
CONDITION_LINES = (
    "With Hs near {hs:.1f} m and a {period:.0f}-second primary period, it feels {energy}.",
    "A {period:.0f}-second pulse beneath roughly {hs:.1f} m of swell makes the water {energy}.",
    "The combination of {hs:.1f} m Hs and a {period:.0f}-second period feels {energy}.",
)
WIND_LINES = {
    "calm/light": (
        "The {wind_dir} wind is light at {wind_speed:.1f} m/s, leaving little surface texture.",
        "A faint {wind_dir} breeze of {wind_speed:.1f} m/s barely interrupts the water.",),
    "favourable": (
        "A favourable {wind_dir} wind at {wind_speed:.1f} m/s helps groom the surface.",
        "The {wind_dir} wind, around {wind_speed:.1f} m/s, arrives from a favourable quarter.",),
    "unfavourable": (
        "An unfavourable {wind_dir} wind at {wind_speed:.1f} m/s asks for adaptability.",
        "The {wind_dir} wind, near {wind_speed:.1f} m/s, works against clean organisation.",),
}
HEADLINES = {
    "Aries": ("Commit After the Pause", "Fire Meets Moving Water"),
    "Taurus": ("Trust the Patient Pulse", "Wait for the True Line"),
    "Gemini": ("Read the Shifting Peak", "One Choice Among Many"),
    "Cancer": ("Let the Water Speak", "Intuition Finds a Line"),
    "Leo": ("Confidence Without Performance", "A Generous Line Appears"),
    "Virgo": ("Precision in Motion", "Refine the Take-off"),
    "Libra": ("Balance Finds the Peak", "Effort Meets Ease"),
    "Scorpio": ("Depth Before Commitment", "Meet Power Calmly"),
    "Sagittarius": ("Explore with Respect", "A Wider Horizon Calls"),
    "Capricorn": ("Patience Builds the Session", "Positioning Is the Work"),
    "Aquarius": ("Find the Unusual Line", "Observe, Then Experiment"),
    "Pisces": ("Feel the Hidden Tempo", "Dream with Open Eyes"),
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
        wind_quality, wind_feel = "calm/light", "barely textured by wind"
    elif favourable:
        wind_quality, wind_feel = "favourable", "groomed by a favourable local wind"
    else:
        wind_quality, wind_feel = "unfavourable", "ruffled by an unfavourable local wind"

    return {
        "location": location, "valid_time_utc": str(pd.Timestamp(row["valid_time_utc"])),
        "wave_height_m": round(hs, 2), "primary_period_s": round(period, 1),
        "wave_direction": None if pd.isna(wave_direction) else compass_direction(wave_direction),
        "wind_speed_m_s": round(wind_speed, 1), "wind_direction": compass_direction(wind_direction),
        "wind_direction_deg": round(wind_direction), "wind_quality": wind_quality,
        "favourable_wind_rule": SPOT_RULES[location]["label"], "ocean_mood": mood,
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
    summary = (f"Hs {conditions['wave_height_m']:.1f} m at {conditions['primary_period_s']:.0f} s, "
               f"with {conditions['wind_direction']} wind at {conditions['wind_speed_m_s']:.1f} m/s "
               f"({conditions['wind_quality']}). The ocean feels {conditions['ocean_feeling']}.")
    values = {"location": conditions["location"], "mood": conditions["ocean_mood"],
              "hs": conditions["wave_height_m"], "period": conditions["primary_period_s"],
              "energy": conditions["period_feel"], "wind_dir": conditions["wind_direction"],
              "wind_speed": conditions["wind_speed_m_s"]}
    reports = []
    for sign in STAR_SIGNS:
        rng = _rng(conditions, sign)
        gift, lesson, actions = SIGN_VOICES[sign]
        reading = " ".join((rng.choice(OPENINGS).format(**values),
                            rng.choice(CONDITION_LINES).format(**values),
                            rng.choice(WIND_LINES[conditions["wind_quality"]]).format(**values),
                            f"Your {gift} is useful here. {lesson}"))
        reports.append(Horoscope(sign, rng.choice(HEADLINES[sign]), reading,
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
