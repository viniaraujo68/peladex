import { DEFAULT_UNIT } from './metrics.js';

export const DEFAULT_SORT = /** @type {import('@viniaraujo68/plinth/table').SortState} */ ({
	key: 'win_rate',
	direction: 'desc'
});

/** @param {URL} url @param {Record<string, string|null>} updates */
export function withParams(url, updates) {
	const next = new URL(url);
	for (const [key, value] of Object.entries(updates)) {
		if (value === null) next.searchParams.delete(key);
		else next.searchParams.set(key, value);
	}
	return next;
}

/** @param {URLSearchParams} params @returns {import('@viniaraujo68/plinth/table').SortState} */
export function readSort(params) {
	return {
		key: params.get('sort') ?? DEFAULT_SORT.key,
		direction: params.get('dir') === 'asc' ? 'asc' : 'desc'
	};
}

/** @param {import('@viniaraujo68/plinth/table').SortState} sort */
export function sortParams(sort) {
	return {
		sort: sort.key === DEFAULT_SORT.key && sort.direction === 'desc' ? null : sort.key,
		dir: sort.direction === 'asc' ? 'asc' : null
	};
}

/** @param {import('./metrics.js').Unit} unit */
export function unitParams(unit) {
	return { per: unit === DEFAULT_UNIT ? null : unit };
}
