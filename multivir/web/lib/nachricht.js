// Nachrichten an die Lumatrix im Zeilenprotokoll (siehe wetter/protokoll.py und docs/adr/0002).

/** JSON-Zeile, in der alle Zeichen ausserhalb von ASCII als \uXXXX stehen. */
export function zeile(nachricht) {
    const json = JSON.stringify(nachricht).replace(
        /[\u0080-￿]/g,
        (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"),
    );
    return json + "\n";
}

/** Zeitverschiebung des Rechners zu UTC in Sekunden (Sommerzeit eingerechnet). */
export function versatzRechner(datum) {
    return -datum.getTimezoneOffset() * 60;
}

/**
 * Eine Nachricht "setzen". Stellt immer die Uhr; die übrigen Felder sind freiwillig:
 * standort, wetter ({tage, versatz}), nachtruhe ([beginn, ende] in Minuten).
 */
export function setzen(datum, { standort, wetter, nachtruhe } = {}) {
    const n = {
        befehl: "setzen",
        jetzt: Math.floor(datum.getTime() / 1000),
        versatz_rechner: versatzRechner(datum),
    };
    if (standort) n.standort = { name: standort.name, lat: standort.lat, lon: standort.lon };
    if (wetter) {
        n.tage = wetter.tage;
        n.versatz_standort = wetter.versatz;
    }
    if (nachtruhe) n.nachtruhe = nachtruhe;
    return n;
}

export const STATUS = { befehl: "status" };

/** "22:30" → 1350 */
export function minutenAusUhrzeit(text) {
    const [h, m] = text.split(":").map(Number);
    return h * 60 + m;
}

/** 1350 → "22:30" */
export function uhrzeitAusMinuten(minuten) {
    const h = Math.floor(minuten / 60);
    return `${String(h).padStart(2, "0")}:${String(minuten % 60).padStart(2, "0")}`;
}

/** Zerlegt einen Strom von Textstücken in Zeilen. */
export class Zeilenpuffer {
    #rest = "";

    hinzu(text) {
        const teile = (this.#rest + text).split("\n");
        this.#rest = teile.pop();
        return teile.map((z) => z.replace(/\r$/, "")).filter((z) => z.length > 0);
    }
}
