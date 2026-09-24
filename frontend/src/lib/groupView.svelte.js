import { tick } from 'svelte';
import { goto } from '$app/navigation';
import { page } from '$app/state';
import { withSearchParams } from '@viniaraujo68/plinth/routing';
import { sortFromParams, sortToParams } from '@viniaraujo68/plinth/table';
import { DEFAULT_UNIT, parseUnit } from './metrics.js';
import { revealPanelStart, scrollParent } from './scroll.js';

/** @type {import('@viniaraujo68/plinth/table').SortState} */
export const DEFAULT_SORT = { key: 'win_rate', direction: 'desc' };

/** @param {Record<string, string|null>} updates */
export function replaceParams(updates) {
	return goto(withSearchParams(page.url, updates), {
		keepFocus: true,
		noScroll: true,
		replaceState: true
	});
}

/** @param {URLSearchParams} params @param {string} key */
export function readIdParam(params, key) {
	const value = Number(params.get(key));
	return Number.isInteger(value) && value > 0 ? value : null;
}

/** @param {{ a: number|null, b: number|null }} pick */
export function pickParams(pick) {
	return {
		a: pick.a === null ? null : String(pick.a),
		b: pick.b === null ? null : String(pick.b)
	};
}

/**
 * @template {string} Tab
 * @param {{ tabIds: Tab[], defaultTab: Tab }} options
 */
export function createGroupView({ tabIds, defaultTab }) {
	let panel = $state(/** @type {HTMLElement|undefined} */ (undefined));
	let boardScroll = 0;

	const params = () => page.url.searchParams;

	const view = {
		get tab() {
			const requested = /** @type {Tab|null} */ (params().get('tab'));
			return requested && tabIds.includes(requested) ? requested : defaultTab;
		},
		get unit() {
			return parseUnit(params().get('per'));
		},
		get sort() {
			return sortFromParams(params(), DEFAULT_SORT);
		},
		get focus() {
			return /** @type {import('./metrics.js').MetricId|null} */ (params().get('focus'));
		},
		get panel() {
			return panel;
		},
		set panel(element) {
			panel = element;
		},
		/** @param {string} id */
		setTab(id) {
			if (id === view.tab) return;
			goto(withSearchParams(page.url, { tab: id === defaultTab ? null : id }), {
				keepFocus: true,
				noScroll: true
			});
		},
		/** @param {import('./metrics.js').Unit} unit */
		setUnit(unit) {
			return replaceParams({ per: unit === DEFAULT_UNIT ? null : unit });
		},
		/** @param {import('@viniaraujo68/plinth/table').SortState} sort */
		setSort(sort) {
			return replaceParams(sortToParams(sort, DEFAULT_SORT));
		},
		/** @param {string|null} value */
		async setFocus(value) {
			const scroller = panel ? scrollParent(panel) : null;
			if (value && !view.focus && scroller) boardScroll = scroller.scrollTop;
			await replaceParams({ focus: value });
			await tick();
			if (!panel || !scroller) return;
			if (value) revealPanelStart(panel);
			else scroller.scrollTop = boardScroll;
		}
	};
	return view;
}
