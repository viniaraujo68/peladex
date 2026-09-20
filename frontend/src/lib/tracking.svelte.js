import { getContext, setContext } from 'svelte';

const KEY = Symbol('peladex.tracking');

/** @typedef {{ trackScorers: boolean, trackAssists: boolean }} Tracking */

/** @type {Tracking} */
const DEFAULT = { trackScorers: true, trackAssists: false };

/** @param {Tracking} source */
export function setTrackingContext(source) {
	setContext(KEY, source);
}

/** @returns {Tracking} */
export function getTracking() {
	return getContext(KEY) ?? DEFAULT;
}
