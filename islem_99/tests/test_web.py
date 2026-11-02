"""Internet lookups: intent detection, parsing and fallbacks, all offline with fakes."""
import unittest
from unittest.mock import patch

from companion_pc import web
from companion_pc.__main__ import Web

PLANS = (
    ("Wie ist das Wetter in Zürich?", ("weather", "Zürich", 0)),
    ("Wie wird das Wetter morgen in Bern?", ("weather", "Bern", 1)),
    ("What's the weather like in New York tomorrow?", ("weather", "New York", 1)),
    ("wetter in st. gallen heute", ("weather", "st. gallen", 0)),
    ("Wie ist das Wetter in der Schweiz übermorgen", ("weather", "Schweiz", 2)),
    ("Brauche ich morgen einen Regenschirm?", ("weather", None, 1)),
    ("Wie ist das Wetter bei dir?", ("weather", None, 0)),
    ("Buddy, such mal im Internet wer das Matterhorn zuerst bestiegen hat",
     ("search", "wer das Matterhorn zuerst bestiegen hat")),
    ("Kannst du nachschauen, wann die Sonne untergeht?", ("search", "wann die Sonne untergeht")),
    ("Look up the height of Mount Everest", ("search", "the height of Mount Everest")),
    # Must not go online:
    ("Ich habe heute Pizza gegessen.", None), ("Guten Morgen Buddy!", None), ("Mir ist kalt.", None),
    ("Ich suche meine Schlüssel.", None), ("Wie ist dein aktueller Status?", None),
    ("Ich war heute online shoppen.", None),
)

LAST = ("weather", "Bern", 0)
FOLLOW_UPS = (
    ("Und morgen?", ("weather", "Bern", 1)),
    ("Und in Basel?", ("weather", "Basel", 0)),
    ("And London?", ("weather", "London", 0)),
    ("What about Paris tomorrow?", ("weather", "Paris", 1)),
    ("Und wie geht es dir?", None),
    ("Und dann habe ich Pizza gegessen und war müde.", None),
)

DDG_PAGE = """
<div class="result results_links"><h2 class="result__title">
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fde.wikipedia.org%2Fwiki%2FMatterhorn&amp;rut=1">Matterhorn &ndash; Wikipedia</a></h2>
<a class="result__snippet" href="//x">Erstbesteigung <b>1865</b> durch Edward Whymper.</a></div>
<div class="result result--ad"><a class="result__a" href="https://duckduckgo.com/y.js?ad_domain=shop.ch">Ad</a>
<a class="result__snippet" href="//x">Kaufen!</a></div>
"""


class PlanTests(unittest.TestCase):
    def test_plans(self):
        for text, expected in PLANS:
            self.assertEqual(web.plan_lookup(text), expected, text)

    def test_follow_ups_only_after_weather(self):
        for text, expected in FOLLOW_UPS:
            self.assertEqual(web.plan_lookup(text, LAST), expected, text)
        self.assertIsNone(web.plan_lookup("Und morgen?"))


class ParseTests(unittest.TestCase):
    def test_duckduckgo_results_without_ads(self):
        self.assertEqual(web.parse_ddg(DDG_PAGE),
                         [("Matterhorn – Wikipedia", "Erstbesteigung 1865 durch Edward Whymper.", "de.wikipedia.org")])

    def test_weather_text(self):
        def fake(url, params=None):
            if "geocoding" in url:
                return {"results": [{"name": "Bern", "country_code": "CH", "latitude": 46.9, "longitude": 7.4}]}
            return {"current": {"temperature_2m": 11.6, "weather_code": 61, "wind_speed_10m": 7.2},
                    "daily": {"weather_code": [61, 0, 3], "temperature_2m_max": [14.4, 18.2, 12],
                              "temperature_2m_min": [6.5, 7, 5], "precipitation_probability_max": [80, 5, 30]}}
        with patch.object(web, "fetch_json", fake):
            text, place = web.weather("Bern", 0, "de")
            self.assertEqual(place, "Bern")
            self.assertIn("Wetter heute in Bern (CH): leichter Regen, 6 bis 14 Grad, Regenwahrscheinlichkeit 80 %", text)
            self.assertIn("Jetzt gerade: 12 Grad", text)
            text, _ = web.weather("Bern", 1, "en")
            self.assertIn("Weather tomorrow in Bern (CH): clear sky, 7 to 18 degrees, 5 % chance of rain", text)
            self.assertNotIn("Right now", text)

    def test_unknown_place(self):
        with patch.object(web, "fetch_json", lambda url, params=None: {}):
            with self.assertRaisesRegex(web.WebError, "nicht gefunden"):
                web.weather("Nirgendwo", 0)

    def test_search_falls_back_to_wikipedia(self):
        def offline(*args, **kwargs):
            raise web.WebError("Internet nicht erreichbar")
        with patch.object(web, "duckduckgo", offline), \
             patch.object(web, "wikipedia", lambda q, lang: ("Matterhorn", "Berg in den Alpen.", "de.wikipedia.org")):
            text, sources = web.search("Matterhorn")
        self.assertEqual(text, "1. Matterhorn (de.wikipedia.org): Berg in den Alpen.")
        with patch.object(web, "duckduckgo", offline), patch.object(web, "wikipedia", offline):
            with self.assertRaises(web.WebError):
                web.search("Matterhorn")


class SessionTests(unittest.TestCase):
    def test_home_town_follow_up_and_failure_note(self):
        calls = []

        def fake_weather(place, day, lang):
            calls.append((place, day))
            return "Wetter in {}".format(place), place
        session = Web(city="Zürich")
        with patch.object(web, "weather", fake_weather), patch("builtins.print"):
            session.run(session.plan("Wie ist das Wetter in London?"), "de")
            session.run(session.plan("Und morgen?"), "de")
            session.run(session.plan("Brauche ich einen Regenschirm?"), "de")  # home town again
            self.assertIsNone(session.plan("Erzähl mir einen Witz"))
            self.assertIsNone(session.plan("Und morgen?"))  # follow-up chain ended
        self.assertEqual(calls, [("London", 0), ("London", 1), ("Zürich", 0)])

        def broken(place, day, lang):
            raise web.WebError("Internet nicht erreichbar")
        with patch.object(web, "weather", broken), patch("builtins.print"):
            note = session.run(("weather", "Bern", 0), "de")
        self.assertIn("could not find it", note)


if __name__ == "__main__":
    unittest.main()
