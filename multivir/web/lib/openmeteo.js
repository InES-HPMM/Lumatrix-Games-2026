// Abfragen bei Open-Meteo (gratis, ohne Key, CORS erlaubt) und Aufbereitung der Antworten.

export const TAGE = 16;

export function wetterUrl(lat, lon) {
    const p = new URLSearchParams({
        latitude: String(lat),
        longitude: String(lon),
        daily: "weather_code,temperature_2m_max,temperature_2m_min",
        timezone: "auto",
        forecast_days: String(TAGE),
    });
    return `https://api.open-meteo.com/v1/forecast?${p}`;
}

/**
 * Wetterdaten im Format der Lumatrix: tage = [[datum, code, max, min], ...] in der Ortszeit
 * des Standorts, versatz = dessen Zeitverschiebung in Sekunden.
 */
export function wetterAusAntwort(json) {
    const d = json?.daily;
    if (!d || !Array.isArray(d.time) || typeof json.utc_offset_seconds !== "number") {
        throw new Error("Unerwartete Antwort von Open-Meteo");
    }
    const tage = d.time.slice(0, TAGE).map((datum, i) => [
        datum,
        ganzzahlOderNull(d.weather_code?.[i]),
        zahlOderNull(d.temperature_2m_max?.[i]),
        zahlOderNull(d.temperature_2m_min?.[i]),
    ]);
    return { tage, versatz: json.utc_offset_seconds };
}

function zahlOderNull(x) {
    return typeof x === "number" && Number.isFinite(x) ? Math.round(x * 10) / 10 : null;
}

function ganzzahlOderNull(x) {
    return Number.isInteger(x) ? x : null;
}

export function sucheUrl(name) {
    const p = new URLSearchParams({ name, count: "8", language: "de", format: "json" });
    return `https://geocoding-api.open-meteo.com/v1/search?${p}`;
}

/** Treffer der Ortssuche als [{name, lat, lon, beschreibung}]. */
export function orteAusSuche(json) {
    return (json?.results ?? []).map((r) => ({
        name: r.name,
        lat: r.latitude,
        lon: r.longitude,
        beschreibung: [r.name, r.admin1, r.country_code].filter(Boolean).join(", "),
    }));
}

/** Standort aus den Koordinaten des Rechners (Open-Meteo kennt keine Rückwärtssuche). */
export function eigenerStandort(lat, lon) {
    const r = (x) => Math.round(x * 1000) / 1000;
    return { name: `Mein Standort (${r(lat)}, ${r(lon)})`, lat: r(lat), lon: r(lon) };
}
