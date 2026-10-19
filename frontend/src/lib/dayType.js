import { getContext, setContext } from 'svelte';
import { t } from './i18n.svelte.js';

/** @typedef {import('./types.js').DayType} DayType */

/** @type {DayType[]} */
export const DAY_TYPES = ['rotation', 'single', 'all'];

/** @param {URLSearchParams} params @returns {DayType|null} */
export function dayTypeParam(params) {
	const value = /** @type {DayType} */ (params.get('day_type'));
	return DAY_TYPES.includes(value) ? value : null;
}

/** @param {DayType|null} dayType */
export function dayTypeQuery(dayType) {
	return dayType ? `day_type=${dayType}` : '';
}

/** @param {string} href @param {DayType|null} dayType */
export function withDayType(href, dayType) {
	if (!dayType) return href;
	return `${href}${href.includes('?') ? '&' : '?'}${dayTypeQuery(dayType)}`;
}

/** @param {import('./types.js').Days} days */
export function hasBothDayTypes(days) {
	return days.rotation_matchdays > 0 && days.single_game_matchdays > 0;
}

const KEY = Symbol('peladex.dayType');

/** @type {import('./metrics.js').Unit[]} */
export const SINGLE_GAME_UNITS = ['total', 'match'];

/** @param {() => import('./types.js').Days|null|undefined} getDays */
export function setDayTypeContext(getDays) {
	setContext(KEY, {
		get single() {
			return getDays()?.day_type === 'single';
		}
	});
}

/** @returns {{ single: boolean }} */
export function getDayTypeView() {
	return getContext(KEY) ?? { single: false };
}

/** @param {import('./metrics.js').Unit} unit @param {boolean} single */
export function visibleUnit(unit, single) {
	return single && unit === 'day' ? 'match' : unit;
}

export function dayTypeOptions() {
	return DAY_TYPES.map((id) => ({ id, label: t(`dayType.${id}`) }));
}
