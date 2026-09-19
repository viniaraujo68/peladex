import pt from './i18n/pt.js';
import en from './i18n/en.js';

/** @typedef {'pt'|'en'} Locale */
/** @typedef {string | { one: string, other: string }} Phrase */

/** @type {Record<Locale, Record<string, Phrase>>} */
const dicts = { pt, en };
const STORAGE_KEY = 'peladex.locale';
const TAGS = { pt: 'pt-BR', en: 'en-US' };

/** @returns {Locale} */
function initialLocale() {
	if (typeof window === 'undefined') return 'pt';
	try {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved === 'pt' || saved === 'en') return saved;
	} catch {
		// storage blocked
	}
	return typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('pt')
		? 'pt'
		: 'en';
}

export const i18n = $state({ locale: /** @type {Locale} */ (initialLocale()) });

/** @param {Locale} l */
function applyLang(l) {
	if (typeof document !== 'undefined') document.documentElement.lang = TAGS[l] ?? TAGS.pt;
}

/** @param {Locale} l */
export function setLocale(l) {
	if (l !== 'pt' && l !== 'en') return;
	if (typeof window === 'undefined') return;
	i18n.locale = l;
	try {
		localStorage.setItem(STORAGE_KEY, l);
	} catch {
		// storage blocked
	}
	applyLang(l);
}

applyLang(i18n.locale);

export function localeTag() {
	return TAGS[i18n.locale] ?? TAGS.pt;
}

/** @param {string} str @param {Record<string, any>} [params] */
function interpolate(str, params) {
	if (!params) return str;
	return str.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m));
}

/**
 * @param {string} key
 * @param {Record<string, any>} [params]
 */
export function t(key, params) {
	const dict = dicts[i18n.locale] ?? dicts.pt;
	const entry = dict[key];
	const value =
		entry && typeof entry === 'object' ? (params?.count === 1 ? entry.one : entry.other) : entry;
	if (typeof value !== 'string') return key;
	return interpolate(value, params);
}
