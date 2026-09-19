import { createFormatters } from '@viniaraujo68/plinth/formatters';
import { i18n, localeTag } from './i18n.svelte.js';

/** @type {Map<string, import('@viniaraujo68/plinth/formatters').Formatters>} */
const cache = new Map();

/** @param {string} tag */
function formattersFor(tag) {
	const cached = cache.get(tag);
	if (cached) return cached;
	const built = createFormatters(tag, {
		percent: { maximumFractionDigits: 1 },
		number: { maximumFractionDigits: 2 }
	});
	cache.set(tag, built);
	return built;
}

const active = $derived(formattersFor(localeTag()));

/** @param {number|null|undefined} rate */
export function formatRate(rate) {
	if (rate === null || rate === undefined) return '—';
	return active.percent(rate);
}

/** @param {number|null|undefined} rate */
export function formatRateDelta(rate) {
	if (rate === null || rate === undefined) return '—';
	const sign = rate > 0 ? '+' : '';
	return sign + active.percent(rate);
}

/** @param {number|null|undefined} value */
export function formatNumber(value) {
	if (value === null || value === undefined) return '—';
	return active.number(value);
}

/** @param {number|null|undefined} value */
export function rateClass(value) {
	if (value === null || value === undefined) return '';
	if (value > 0) return 'rate-pos';
	if (value < 0) return 'rate-neg';
	return '';
}

/** @param {string|null|undefined} date */
export function formatMatchdayDate(date) {
	if (!date) return '';
	return new Date(date + 'T00:00:00').toLocaleDateString(localeTag(), {
		day: '2-digit',
		month: 'long',
		year: 'numeric'
	});
}

/** @param {string|null|undefined} date */
export function formatShortDate(date) {
	if (!date) return '';
	return new Date(date + 'T00:00:00').toLocaleDateString(localeTag(), {
		day: '2-digit',
		month: 'short'
	});
}

/** @param {string|null|undefined} date */
export function formatWeekday(date) {
	if (!date) return '';
	return new Date(date + 'T00:00:00').toLocaleDateString(localeTag(), { weekday: 'long' });
}

export { i18n };
