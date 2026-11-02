"""Internet lookups without API keys or costs.

- Weather: Open-Meteo geocoding + forecast API (free, no key).
- Web search: DuckDuckGo HTML results (unofficial, may change or rate-limit),
  falling back to the official Wikipedia API.
Only called when the user clearly asks (see plan_lookup); nothing runs in the background.
"""
import html
import json
import re
from urllib.error import URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

TIMEOUT = 8
MAX_BYTES = 2 * 1024 * 1024
MAX_INFO = 1500
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0) PixelBuddy/1.0 (local hobby companion)"


class WebError(Exception):
    pass


def fetch(url, params=None, data=None):
    """GET (or POST form data) and return bytes; system proxy settings are used."""
    if params:
        url += "?" + urlencode(params)
    body = urlencode(data).encode() if data else None
    request = Request(url, data=body, headers={"User-Agent": USER_AGENT,
                                               "Accept-Language": "de-CH,de;q=0.9,en;q=0.8"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return response.read(MAX_BYTES)
    except (URLError, OSError, ValueError) as exc:
        raise WebError("Internet nicht erreichbar ({})".format(getattr(exc, "reason", exc))) from exc


def fetch_json(url, params=None):
    try:
        return json.loads(fetch(url, params))
    except ValueError as exc:
        raise WebError("Unerwartete Antwort von " + urlparse(url).netloc) from exc


# --- Deciding what to look up ------------------------------------------------

WEATHER = re.compile(r"\b(wetter\w*|regnet|regen|regenschirm|schneit|schnee|gewitter|temperatur\w*"
                     r"|weather|rain\w*|snow\w*|umbrella|forecast|thunderstorm|temperature)\b", re.IGNORECASE)
# Only explicit requests: "Ich suche meine Schluessel" or "dein aktueller Status" must not search.
SEARCH = re.compile(r"\bsuch (mal |doch |bitte )?\w|\bgoogle\w*|\bgoogel\w*|\brecherchier\w*|\bim (internet|netz)\b"
                    r"|\bschau (mal |doch |bitte )?nach\b|\b(kannst|könntest|koenntest) du\b.*\b(suchen|nachschauen"
                    r"|googeln|recherchieren)\b|\bsearch (for|the web)\b|\blook up\b|\bnews\b|\bnachrichten\b"
                    r"|\bneuigkeiten\b|\blatest\b", re.IGNORECASE)
PLACE_START = re.compile(r"\b(?:in|im|für|fuer|bei|at|for|around)\s+(.+)", re.IGNORECASE)
ARTICLES = {"der", "die", "das", "dem", "den", "the"}
NOT_PLACE = {"heute", "morgen", "übermorgen", "uebermorgen", "today", "tomorrow", "tonight", "jetzt", "now",
             "dir", "mir", "uns", "euch", "you", "me", "us", "hier", "here", "draussen", "draußen", "outside",
             "wird", "werden", "ist", "sein", "so", "aus", "be", "is", "like", "going", "will", "nächste",
             "nächsten", "next", "this", "diese", "dieses", "wetter", "weather", "abend", "nachmittag", "woche",
             "week", "weekend", "wochenende", "früh", "morning", "evening", "regen", "rain", "einen", "a"}
FILLER = re.compile(r"\b(buddy|badi|pixel|hey|hallo|bitte|please|mal|doch|kannst du|könntest du|can you|could you"
                    r"|für mich|for me|im internet|im netz|online|google|googeln|googel|such\w*|search( for)?"
                    r"|look up|recherchier\w*|nachschauen|schau nach|und sag mir|and tell me)\b",
                    re.IGNORECASE)


def find_place(sentence):
    match = PLACE_START.search(sentence)
    if not match:
        return None
    words = []
    for raw in match.group(1).split():
        word = raw.strip(",.!?;:\"'")
        if not words and word.lower() in ARTICLES:
            continue
        if word.lower() in NOT_PLACE or not word or len(words) == 3:
            break
        if word.lower() in ("st", "san", "sankt") and raw.endswith("."):
            words.append(word + ".")  # St. Gallen, St. Moritz
            continue
        words.append(word)
        if raw[-1:] in ",.!?;:":
            break
    return " ".join(words) or None


def find_day(text):
    lower = text.lower()
    if re.search(r"übermorgen|uebermorgen|day after tomorrow", lower):
        return 2
    if re.search(r"\b(morgen|tomorrow)\b", lower) and "guten morgen" not in lower:
        return 1
    return 0


FOLLOW_UP = re.compile(r"^\W*(und|and|what about|how about|wie sieht'?s|und wie)\b(.*)", re.IGNORECASE)
DAY_WORD = re.compile(r"\b(heute|morgen|übermorgen|uebermorgen|today|tomorrow)\b", re.IGNORECASE)
FOLLOW_SKIP = NOT_PLACE | ARTICLES | {"wie", "what", "how", "about", "sieht", "es", "aus", "mit", "dort", "there"}


def follow_up(text, last):
    """'Und morgen?' / 'And London?' right after a weather question -> weather plan."""
    match = FOLLOW_UP.search(text)
    if not match or len(text.split()) > 8:
        return None
    rest = match.group(2)
    place = find_place(rest)
    if not place:
        # Without "in"/"for" only capitalised words count: "And London?" yes, "Und wie geht es dir?" no.
        words = [w.strip(",.!?;:") for w in rest.split()]
        words = [w for w in words if w and w.lower() not in FOLLOW_SKIP]
        if words and all(w[0].isupper() for w in words) and len(words) <= 3:
            place = " ".join(words)
    if not place and not DAY_WORD.search(rest):
        return None
    return ("weather", place or last[1], find_day(rest) if DAY_WORD.search(rest) else last[2])


def plan_lookup(text, last=None):
    """Return ("weather", place_or_None, day) / ("search", query) / None.

    last: the previous weather plan (with the place actually used) for follow-ups.
    """
    if last and last[0] == "weather" and not WEATHER.search(text):
        plan = follow_up(text, last)
        if plan:
            return plan
    if WEATHER.search(text):
        return ("weather", find_place(text), find_day(text))
    if SEARCH.search(text):
        query = re.sub(r"\s+", " ", FILLER.sub(" ", text)).strip(" ,.!?:")
        return ("search", query or text)
    return None


# --- Weather -------------------------------------------------------------------

WMO = {
    0: ("klar", "clear sky"), 1: ("ueberwiegend klar", "mainly clear"), 2: ("teilweise bewoelkt", "partly cloudy"),
    3: ("bedeckt", "overcast"), 45: ("Nebel", "fog"), 48: ("Reifnebel", "freezing fog"),
    51: ("leichter Nieselregen", "light drizzle"), 53: ("Nieselregen", "drizzle"), 55: ("starker Nieselregen", "dense drizzle"),
    56: ("gefrierender Nieselregen", "freezing drizzle"), 57: ("gefrierender Nieselregen", "freezing drizzle"),
    61: ("leichter Regen", "light rain"), 63: ("Regen", "rain"), 65: ("starker Regen", "heavy rain"),
    66: ("gefrierender Regen", "freezing rain"), 67: ("gefrierender Regen", "freezing rain"),
    71: ("leichter Schneefall", "light snow"), 73: ("Schneefall", "snow"), 75: ("starker Schneefall", "heavy snow"),
    77: ("Schneegriesel", "snow grains"), 80: ("leichte Regenschauer", "light rain showers"),
    81: ("Regenschauer", "rain showers"), 82: ("heftige Regenschauer", "violent rain showers"),
    85: ("leichte Schneeschauer", "light snow showers"), 86: ("Schneeschauer", "snow showers"),
    95: ("Gewitter", "thunderstorm"), 96: ("Gewitter mit Hagel", "thunderstorm with hail"),
    99: ("Gewitter mit Hagel", "thunderstorm with hail"),
}
DAYS = {"de": ("heute", "morgen", "uebermorgen"), "en": ("today", "tomorrow", "the day after tomorrow")}


def describe_code(code, lang):
    return WMO.get(code, ("unbekannt", "unknown"))[0 if lang == "de" else 1]


def weather(place, day=0, lang="de"):
    """Short factual weather text for the AI, in the user's language."""
    found = fetch_json("https://geocoding-api.open-meteo.com/v1/search",
                       {"name": place, "count": 1, "language": lang, "format": "json"}).get("results")
    if not found:
        raise WebError("Ort '{}' nicht gefunden".format(place))
    spot = found[0]
    data = fetch_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": spot["latitude"], "longitude": spot["longitude"], "timezone": "auto", "forecast_days": 3,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    })
    daily = data["daily"]
    name = "{} ({})".format(spot["name"], spot.get("country_code", "?"))
    label = DAYS[lang if lang in DAYS else "en"][day]
    high, low = round(daily["temperature_2m_max"][day]), round(daily["temperature_2m_min"][day])
    rain = daily["precipitation_probability_max"][day]
    sky = describe_code(daily["weather_code"][day], lang)
    if lang == "de":
        text = "Wetter {} in {}: {}, {} bis {} Grad, Regenwahrscheinlichkeit {} %.".format(
            label, name, sky, low, high, rain)
        if day == 0:
            now = data["current"]
            text += " Jetzt gerade: {} Grad, {}, Wind {} km/h.".format(
                round(now["temperature_2m"]), describe_code(now["weather_code"], lang), round(now["wind_speed_10m"]))
    else:
        text = "Weather {} in {}: {}, {} to {} degrees, {} % chance of rain.".format(
            label, name, sky, low, high, rain)
        if day == 0:
            now = data["current"]
            text += " Right now: {} degrees, {}, wind {} km/h.".format(
                round(now["temperature_2m"]), describe_code(now["weather_code"], lang), round(now["wind_speed_10m"]))
    return text + " (Open-Meteo)", spot["name"]


# --- Web search ------------------------------------------------------------------

RESULT = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
                    r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)


def clean_html(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def parse_ddg(page):
    results = []
    for href, title, snippet in RESULT.findall(page):
        target = parse_qs(urlparse(html.unescape(href)).query).get("uddg", [href])[0]
        if "duckduckgo.com/y.js" in href or "ad_domain" in href:
            continue  # sponsored result
        domain = urlparse(target).netloc.replace("www.", "")
        results.append((clean_html(title), clean_html(snippet), domain))
    return results


def duckduckgo(query, lang="de", limit=4):
    page = fetch("https://html.duckduckgo.com/html/",
                 data={"q": query, "kl": "ch-de" if lang == "de" else "us-en"}).decode("utf-8", "replace")
    return parse_ddg(page)[:limit]


def wikipedia(query, lang="de"):
    base = "https://{}.wikipedia.org".format("de" if lang == "de" else "en")
    hits = fetch_json(base + "/w/api.php", {"action": "query", "list": "search", "srsearch": query,
                                            "srlimit": 1, "format": "json"})["query"]["search"]
    if not hits:
        return None
    title = hits[0]["title"]
    summary = fetch_json(base + "/api/rest_v1/page/summary/" + quote(title.replace(" ", "_")))
    return title, summary.get("extract", ""), urlparse(base).netloc


def search(query, lang="de"):
    """Short text with the best snippets for the AI; raises WebError if nothing worked."""
    results, problem = [], None
    try:
        results = duckduckgo(query, lang)
    except WebError as exc:
        problem = exc
    if len(results) < 2:
        try:
            wiki = wikipedia(query, lang)
        except (WebError, KeyError) as exc:
            wiki, problem = None, problem or exc
        if wiki and wiki[1]:
            results.append(wiki)
    if not results:
        raise problem or WebError("Keine Ergebnisse fuer '{}'".format(query))
    lines = ["{}. {} ({}): {}".format(i, title, domain, snippet) for i, (title, snippet, domain) in enumerate(results, 1)]
    return "\n".join(lines)[:MAX_INFO], ", ".join(sorted({domain for _, _, domain in results}))


def lookup(plan, lang="de", default_place=None):
    """Run a plan from plan_lookup. Returns (info for the AI, short source note, place used)."""
    if plan[0] == "weather":
        place = plan[1] or default_place
        if not place:
            return ("The user asked about the weather but did not say where. "
                    "Ask which city (tip: --city sets a home town)."), "kein Ort", None
        text, used = weather(place, plan[2], lang)
        return "Current weather data:\n" + text, "Open-Meteo, " + used, used
    text, sources = search(plan[1], lang)
    return ("Web search results for '{}' (fetched just now):\n{}".format(plan[1], text)), sources, None
