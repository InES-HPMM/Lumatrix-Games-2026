// Konfigurationsseite: verbindet sich per Web Serial mit der Lumatrix, holt das Wetter bei
// Open-Meteo und überträgt es (siehe docs/adr/0001 und 0002).

import { eigenerStandort, orteAusSuche, sucheUrl, wetterAusAntwort, wetterUrl } from "./lib/openmeteo.js";
import {
    STATUS,
    Zeilenpuffer,
    minutenAusUhrzeit,
    setzen,
    uhrzeitAusMinuten,
    zeile,
} from "./lib/nachricht.js";
import { naechsteUebertragung } from "./lib/zeitplan.js";

const PICO_VENDOR_ID = 0x2e8a; // Raspberry Pi
const PROTOKOLL_VERSION = 1;
const ANTWORT_TIMEOUT_MS = 4000;
const PRUEFEN_MS = 20 * 1000;

const $ = (id) => document.getElementById(id);

const z = {
    port: null,
    leser: null,
    schreiber: null,
    lumatrix: null, // letzter gemeldeter Zustand
    erfolg: null, // Zeitpunkt der letzten erfolgreichen Übertragung
    fehler: null, // Zeitpunkt des letzten Fehlschlags
    wartend: [], // Auflöser für Antworten, in Sendereihenfolge
    laeuft: false, // eine Übertragung ist im Gang
};

// --- Meldungen und Anzeige ----------------------------------------------------------------------

function melden(text, art = "info") {
    const li = document.createElement("li");
    li.className = art;
    li.textContent = `${new Date().toLocaleTimeString("de-CH")}  ${text}`;
    const liste = $("meldungen");
    liste.prepend(li);
    while (liste.children.length > 50) liste.lastChild.remove();
}

function vorWieLange(ms) {
    const min = Math.round((Date.now() - ms) / 60000);
    if (min < 1) return "gerade eben";
    if (min < 60) return `vor ${min} Min.`;
    return `vor ${Math.floor(min / 60)} Std. ${min % 60} Min.`;
}

function anzeigen() {
    const verbunden = z.port !== null && z.lumatrix !== null;
    $("verbindung").textContent = verbunden ? "verbunden" : z.port ? "verbinde …" : "nicht verbunden";
    $("verbindung").dataset.zustand = verbunden ? "ok" : "aus";
    $("verbinden").hidden = z.port !== null;
    $("trennen").hidden = z.port === null;
    $("aktualisieren").disabled = !verbunden || !z.lumatrix.standort || z.laeuft;
    for (const id of ["suche-feld", "suche-knopf", "mein-standort", "nacht-beginn", "nacht-ende", "nacht-speichern"]) {
        $(id).disabled = !verbunden;
    }

    const l = z.lumatrix;
    $("standort").textContent = l?.standort?.name ?? (verbunden ? "noch keiner gewählt" : "–");
    if (l && l.wetter_zeit) {
        $("letzte").textContent = `${vorWieLange(l.wetter_zeit * 1000)} (${l.tage} Tage)`;
    } else {
        $("letzte").textContent = verbunden ? "noch keine" : "–";
    }
    if (verbunden && l.standort) {
        const n = naechsteUebertragung(z.erfolg, z.fehler);
        $("naechste").textContent =
            n <= Date.now() ? "jetzt" : new Date(n).toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" });
    } else {
        $("naechste").textContent = "–";
    }
    if (l && document.activeElement?.type !== "time") {
        $("nacht-beginn").value = uhrzeitAusMinuten(l.nachtruhe[0]);
        $("nacht-ende").value = uhrzeitAusMinuten(l.nachtruhe[1]);
    }
}

// --- Serielle Verbindung ------------------------------------------------------------------------

async function verbinden(port) {
    if (z.port) return;
    z.port = port;
    anzeigen();
    try {
        await port.open({ baudRate: 115200 });
        await port.setSignals({ dataTerminalReady: true });
    } catch (e) {
        z.port = null;
        anzeigen();
        melden(
            `Verbindung fehlgeschlagen: ${e.message}. Ist die Lumatrix noch in einem anderen Programm (mpremote, Thonny) offen?`,
            "fehler",
        );
        return;
    }
    z.schreiber = port.writable.getWriter();
    lesen(port);
    try {
        zustandUebernehmen(await senden(STATUS));
        melden("Mit der Lumatrix verbunden.");
        if (z.lumatrix.standort) await uebertragen();
    } catch (e) {
        melden(`Die Lumatrix antwortet nicht: ${e.message}`, "fehler");
    }
}

async function lesen(port) {
    const puffer = new Zeilenpuffer();
    const decoder = new TextDecoder();
    z.leser = port.readable.getReader();
    try {
        for (;;) {
            const { value, done } = await z.leser.read();
            if (done) break;
            for (const text of puffer.hinzu(decoder.decode(value, { stream: true }))) zeileEmpfangen(text);
        }
    } catch {
        // Port wurde getrennt
    } finally {
        z.leser.releaseLock();
        z.leser = null;
    }
}

function zeileEmpfangen(text) {
    let nachricht;
    try {
        nachricht = JSON.parse(text);
    } catch {
        melden(`Lumatrix: ${text}`, "geraet"); // z. B. eine Fehlermeldung von MicroPython
        return;
    }
    if (nachricht.hallo) {
        // Die Lumatrix ist neu gestartet und kennt die Uhrzeit nicht mehr.
        zustandUebernehmen(nachricht);
        melden("Die Lumatrix ist neu gestartet.");
        if (nachricht.standort) uebertragen();
        return;
    }
    const aufloeser = z.wartend.shift();
    if (aufloeser) aufloeser(nachricht);
}

function zustandUebernehmen(nachricht) {
    if (nachricht.version !== PROTOKOLL_VERSION) {
        melden(`Die Lumatrix spricht Protokollversion ${nachricht.version}, diese Seite ${PROTOKOLL_VERSION}.`, "fehler");
    }
    z.lumatrix = nachricht;
    anzeigen();
}

async function senden(nachricht) {
    if (!z.schreiber) throw new Error("nicht verbunden");
    const antwort = new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            const i = z.wartend.indexOf(aufloeser);
            if (i >= 0) z.wartend.splice(i, 1);
            reject(new Error("keine Antwort"));
        }, ANTWORT_TIMEOUT_MS);
        const aufloeser = (a) => {
            clearTimeout(timer);
            resolve(a);
        };
        z.wartend.push(aufloeser);
    });
    await z.schreiber.write(new TextEncoder().encode(zeile(nachricht)));
    const a = await antwort;
    if (!a.ok) throw new Error(a.fehler);
    return a;
}

async function trennen() {
    const port = z.port;
    if (!port) return;
    try {
        await z.leser?.cancel();
        z.schreiber?.releaseLock();
        await port.close();
    } catch {
        // schon weg
    }
    getrennt();
}

function getrennt() {
    z.port = z.leser = z.schreiber = z.lumatrix = null;
    z.wartend = [];
    anzeigen();
}

// --- Übertragung --------------------------------------------------------------------------------

async function wetterHolen(standort) {
    const antwort = await fetch(wetterUrl(standort.lat, standort.lon));
    if (!antwort.ok) throw new Error(`Open-Meteo antwortet mit ${antwort.status}`);
    return wetterAusAntwort(await antwort.json());
}

/** Holt das Wetter für den Standort der Lumatrix (oder einen neuen) und überträgt es. */
async function uebertragen(neuerStandort = null) {
    if (z.laeuft || !z.lumatrix) return;
    const standort = neuerStandort ?? z.lumatrix.standort;
    if (!standort) return;
    z.laeuft = true;
    anzeigen();
    try {
        let wetter = null;
        try {
            wetter = await wetterHolen(standort);
        } catch (e) {
            melden(`Wetter konnte nicht geholt werden: ${e.message}. Neuer Versuch in 5 Minuten.`, "fehler");
        }
        // Auch ohne Wetter: Uhr stellen und einen neuen Standort setzen.
        zustandUebernehmen(await senden(setzen(new Date(), { standort: neuerStandort, wetter })));
        if (wetter) {
            z.erfolg = Date.now();
            melden(`Wetter für ${standort.name} übertragen.`);
        } else {
            z.fehler = Date.now();
        }
    } catch (e) {
        z.fehler = Date.now();
        melden(`Übertragung fehlgeschlagen: ${e.message}`, "fehler");
    } finally {
        z.laeuft = false;
        anzeigen();
    }
}

function pruefen() {
    if (z.lumatrix?.standort && !z.laeuft && Date.now() >= naechsteUebertragung(z.erfolg, z.fehler)) {
        uebertragen();
    }
    anzeigen();
}

// --- Standort und Nachtruhe ---------------------------------------------------------------------

async function suchen(ereignis) {
    ereignis.preventDefault();
    const name = $("suche-feld").value.trim();
    const liste = $("treffer");
    liste.replaceChildren();
    if (!name) return;
    try {
        const antwort = await fetch(sucheUrl(name));
        const orte = orteAusSuche(await antwort.json());
        if (orte.length === 0) {
            liste.innerHTML = "<li class='leer'>Kein Ort gefunden.</li>";
            return;
        }
        for (const ort of orte) {
            const li = document.createElement("li");
            const knopf = document.createElement("button");
            knopf.type = "button";
            knopf.textContent = ort.beschreibung;
            knopf.addEventListener("click", () => standortWaehlen(ort));
            li.append(knopf);
            liste.append(li);
        }
    } catch (e) {
        melden(`Ortssuche fehlgeschlagen: ${e.message}`, "fehler");
    }
}

async function standortWaehlen(ort) {
    $("treffer").replaceChildren();
    $("suche-feld").value = "";
    z.erfolg = z.fehler = null;
    await uebertragen({ name: ort.name, lat: ort.lat, lon: ort.lon });
}

function meinStandort() {
    if (!navigator.geolocation) {
        melden("Dieser Browser kennt keinen Standort.", "fehler");
        return;
    }
    navigator.geolocation.getCurrentPosition(
        (p) => standortWaehlen(eigenerStandort(p.coords.latitude, p.coords.longitude)),
        (e) => melden(`Standort nicht verfügbar: ${e.message}`, "fehler"),
        { timeout: 15000 },
    );
}

async function nachtruheSpeichern(ereignis) {
    ereignis.preventDefault();
    const nachtruhe = [minutenAusUhrzeit($("nacht-beginn").value), minutenAusUhrzeit($("nacht-ende").value)];
    try {
        zustandUebernehmen(await senden(setzen(new Date(), { nachtruhe })));
        melden(`Nachtruhe gespeichert: ${$("nacht-beginn").value} bis ${$("nacht-ende").value}.`);
    } catch (e) {
        melden(`Nachtruhe nicht gespeichert: ${e.message}`, "fehler");
    }
}

// --- Start --------------------------------------------------------------------------------------

async function start() {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");

    if (!("serial" in navigator)) {
        $("ohne-serial").hidden = false;
        $("verbinden").disabled = true;
        anzeigen();
        return;
    }

    $("verbinden").addEventListener("click", async () => {
        try {
            const port = await navigator.serial.requestPort({ filters: [{ usbVendorId: PICO_VENDOR_ID }] });
            await verbinden(port);
        } catch {
            // Auswahl abgebrochen
        }
    });
    $("trennen").addEventListener("click", trennen);
    $("aktualisieren").addEventListener("click", () => uebertragen());
    $("suche").addEventListener("submit", suchen);
    $("mein-standort").addEventListener("click", meinStandort);
    $("nachtruhe").addEventListener("submit", nachtruheSpeichern);

    // Einmal freigegebene Lumatrix ohne Klick verbinden, auch nach dem Wiedereinstecken.
    navigator.serial.addEventListener("connect", (e) => verbinden(e.target));
    navigator.serial.addEventListener("disconnect", (e) => {
        if (e.target === z.port) {
            getrennt();
            melden("Die Lumatrix wurde ausgesteckt.");
        }
    });
    const bekannte = (await navigator.serial.getPorts()).filter((p) => p.getInfo().usbVendorId === PICO_VENDOR_ID);
    if (bekannte.length > 0) await verbinden(bekannte[0]);

    setInterval(pruefen, PRUEFEN_MS);
    anzeigen();
}

start();
