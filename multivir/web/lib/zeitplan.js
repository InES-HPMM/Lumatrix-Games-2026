// Wann die nächste Übertragung fällig ist.
// Stündlich nach der letzten erfolgreichen, zusätzlich kurz nach Mitternacht (Zeit des Rechners),
// nach einem Fehler erneut nach fünf Minuten.

export const STUENDLICH_MS = 60 * 60 * 1000;
export const NEUER_VERSUCH_MS = 5 * 60 * 1000;
export const NACH_MITTERNACHT_MS = 60 * 1000;

/** Erster Zeitpunkt kurz nach der nächsten Mitternacht nach `ms` (Ortszeit des Rechners). */
export function naechsteMitternacht(ms) {
    const d = new Date(ms);
    d.setHours(24, 0, 0, 0);
    return d.getTime() + NACH_MITTERNACHT_MS;
}

/**
 * Zeitpunkt (ms) der nächsten Übertragung.
 * @param erfolg  Zeitpunkt der letzten erfolgreichen Übertragung oder null
 * @param fehler  Zeitpunkt des letzten Fehlschlags oder null
 */
export function naechsteUebertragung(erfolg, fehler) {
    if (fehler !== null && (erfolg === null || fehler > erfolg)) {
        return fehler + NEUER_VERSUCH_MS;
    }
    if (erfolg === null) return 0;
    return Math.min(erfolg + STUENDLICH_MS, naechsteMitternacht(erfolg));
}
