import assert from "node:assert/strict";
import { test } from "node:test";

import { orteAusSuche, wetterAusAntwort, wetterUrl } from "../../web/lib/openmeteo.js";
import { Zeilenpuffer, minutenAusUhrzeit, setzen, uhrzeitAusMinuten, zeile } from "../../web/lib/nachricht.js";
import { NEUER_VERSUCH_MS, STUENDLICH_MS, naechsteMitternacht, naechsteUebertragung } from "../../web/lib/zeitplan.js";

test("Wetter-URL fragt 16 Tage in Ortszeit ab", () => {
    const url = new URL(wetterUrl(46.96, 8.37));
    assert.equal(url.searchParams.get("forecast_days"), "16");
    assert.equal(url.searchParams.get("timezone"), "auto");
    assert.match(url.searchParams.get("daily"), /weather_code/);
});

test("Antwort von Open-Meteo wird zu Tagen der Lumatrix", () => {
    const json = {
        utc_offset_seconds: 7200,
        daily: {
            time: ["2026-10-16", "2026-10-17"],
            weather_code: [3, null],
            temperature_2m_max: [18.43, -1.2],
            temperature_2m_min: [9.5, null],
        },
    };
    assert.deepEqual(wetterAusAntwort(json), {
        tage: [
            ["2026-10-16", 3, 18.4, 9.5],
            ["2026-10-17", null, -1.2, null],
        ],
        versatz: 7200,
    });
    assert.throws(() => wetterAusAntwort({ error: true }));
});

test("Treffer der Ortssuche", () => {
    const orte = orteAusSuche({
        results: [{ name: "Stans", latitude: 46.958, longitude: 8.366, admin1: "Nidwalden", country_code: "CH" }],
    });
    assert.deepEqual(orte, [{ name: "Stans", lat: 46.958, lon: 8.366, beschreibung: "Stans, Nidwalden, CH" }]);
    assert.deepEqual(orteAusSuche({}), []);
});

test("Zeilen sind reines ASCII mit Zeilenende", () => {
    const z = zeile({ name: "Zürich" });
    assert.equal(z, '{"name":"Z\\u00fcrich"}\n');
    assert.equal(JSON.parse(z).name, "Zürich");
    assert.ok(!z.includes("\x03"));
});

test("setzen stellt immer die Uhr und schickt nur, was gegeben ist", () => {
    const datum = new Date(Date.UTC(2026, 9, 16, 8, 0, 0));
    const n = setzen(datum, { nachtruhe: [1320, 420] });
    assert.equal(n.befehl, "setzen");
    assert.equal(n.jetzt, Math.floor(datum.getTime() / 1000));
    assert.equal(typeof n.versatz_rechner, "number");
    assert.deepEqual(n.nachtruhe, [1320, 420]);
    assert.ok(!("tage" in n) && !("standort" in n));

    const mitWetter = setzen(datum, { wetter: { tage: [["2026-10-16", 0, 20, 10]], versatz: 7200 } });
    assert.equal(mitWetter.versatz_standort, 7200);
});

test("Uhrzeiten und Minuten", () => {
    assert.equal(minutenAusUhrzeit("22:30"), 1350);
    assert.equal(uhrzeitAusMinuten(420), "07:00");
});

test("Zeilenpuffer setzt Stücke zusammen", () => {
    const p = new Zeilenpuffer();
    assert.deepEqual(p.hinzu('{"ok":'), []);
    assert.deepEqual(p.hinzu('true}\r\n{"a"'), ['{"ok":true}']);
    assert.deepEqual(p.hinzu(":1}\n"), ['{"a":1}']);
});

test("Zeitplan: sofort, stündlich, nach Mitternacht, nach Fehler", () => {
    assert.equal(naechsteUebertragung(null, null), 0);

    const mittag = new Date(2026, 9, 16, 12, 0).getTime();
    assert.equal(naechsteUebertragung(mittag, null), mittag + STUENDLICH_MS);

    const spaet = new Date(2026, 9, 16, 23, 30).getTime();
    const mitternacht = naechsteMitternacht(spaet);
    assert.equal(new Date(mitternacht).getDate(), 17);
    assert.equal(naechsteUebertragung(spaet, null), mitternacht);

    assert.equal(naechsteUebertragung(mittag, mittag + 1000), mittag + 1000 + NEUER_VERSUCH_MS);
    assert.equal(naechsteUebertragung(mittag + 1000, mittag), mittag + 1000 + STUENDLICH_MS);
});
