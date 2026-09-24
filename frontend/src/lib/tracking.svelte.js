import { getContext, setContext } from 'svelte';

const KEY = Symbol('peladex.tracking');

/** @typedef {{ trackScorers: boolean, trackAssists: boolean, showRatings: boolean }} Tracking */

/** @type {Tracking} */
const DEFAULT = { trackScorers: true, trackAssists: false, showRatings: true };

/** @param {Tracking} source */
export function setTrackingContext(source) {
	setContext(KEY, source);
}

/** @returns {Tracking} */
export function getTracking() {
	return getContext(KEY) ?? DEFAULT;
}

/** @param {() => { track_scorers: boolean, track_assists: boolean, show_ratings: boolean }|null|undefined} getGroup */
export function setGroupTracking(getGroup) {
	setTrackingContext({
		get trackScorers() {
			return getGroup()?.track_scorers ?? DEFAULT.trackScorers;
		},
		get trackAssists() {
			return getGroup()?.track_assists ?? DEFAULT.trackAssists;
		},
		get showRatings() {
			return getGroup()?.show_ratings ?? DEFAULT.showRatings;
		}
	});
}
