import { formatShortDate } from '$lib/format.svelte.js';
import { t } from '$lib/i18n.svelte.js';

/** @param {string[]} dates */
const spansYears = (dates) => dates[0].slice(0, 4) !== dates[dates.length - 1].slice(0, 4);

/** @param {string} date @param {string[]} dates */
function dateLabel(date, dates) {
	return spansYears(dates) ? `${formatShortDate(date)} ${date.slice(0, 4)}` : formatShortDate(date);
}

/** @param {string[]} dates */
export function whenSummary(dates) {
	if (dates.length === 1) return t('compare.whenOnce', { date: dateLabel(dates[0], dates) });
	return t('compare.whenRange', {
		count: dates.length,
		first: dateLabel(dates[0], dates),
		last: dateLabel(dates[dates.length - 1], dates)
	});
}
