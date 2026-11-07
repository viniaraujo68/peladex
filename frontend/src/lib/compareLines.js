import { formatAverage, formatNote, formatRate } from './format.svelte.js';
import { t } from './i18n.svelte.js';
import { metricById, metricValue, unitValue } from './metrics.js';

/** @typedef {import('./types.js').PlayerRow} PlayerRow */
/** @typedef {import('./tracking.svelte.js').Tracking} Tracking */
/** @typedef {(value: number|null) => string} Format */

/**
 * @typedef {object} CompareLine
 * @property {string} label
 * @property {string} left
 * @property {string} right
 * @property {number} leftWidth
 * @property {number} rightWidth
 * @property {'a'|'b'|null} winner
 */

/**
 * @param {string} label
 * @param {number|null} left
 * @param {number|null} right
 * @param {Format} format
 * @param {boolean} [lowerWins]
 * @returns {CompareLine}
 */
export function compareLine(label, left, right, format, lowerWins = false) {
	const max = Math.max(left ?? 0, right ?? 0) || 1;
	const leftText = format(left);
	const rightText = format(right);
	const tied = left === null || right === null || leftText === rightText;
	const leftAhead = lowerWins ? (left ?? 0) < (right ?? 0) : (left ?? 0) > (right ?? 0);
	return {
		label,
		left: leftText,
		right: rightText,
		leftWidth: ((left ?? 0) / max) * 100,
		rightWidth: ((right ?? 0) / max) * 100,
		winner: tied ? null : leftAhead ? 'a' : 'b'
	};
}

/**
 * @param {PlayerRow} left
 * @param {PlayerRow} right
 * @param {'match'|'day'} unit
 * @param {Tracking} tracking
 * @returns {CompareLine[]}
 */
export function overallLines(left, right, unit, tracking) {
	const scorers = tracking.trackScorers;
	const assists = scorers && tracking.trackAssists;
	/** @param {'goals'|'assists'|'contributions'|'goals_conceded'} key @param {boolean} [lowerWins] */
	const perUnit = (key, lowerWins = false) =>
		compareLine(
			t(`compare.perUnit.${key}.${unit}`),
			unitValue(left, key, unit),
			unitValue(right, key, unit),
			formatAverage,
			lowerWins
		);
	/** @param {string} label @param {(row: PlayerRow) => number} count */
	const dayShare = (label, count) =>
		compareLine(
			label,
			left.matchdays ? count(left) / left.matchdays : 0,
			right.matchdays ? count(right) / right.matchdays : 0,
			formatRate
		);
	return [
		compareLine(t('compare.metric.win_rate'), left.win_rate, right.win_rate, formatRate),
		...(tracking.showRatings
			? [
					compareLine(
						t('compare.metric.rating'),
						metricValue(left, metricById('rating'), 'total'),
						metricValue(right, metricById('rating'), 'total'),
						formatNote
					)
				]
			: []),
		compareLine(t('ranking.presence'), left.presence, right.presence, formatRate),
		compareLine(
			t('compare.metric.matches_per_matchday'),
			left.matches_per_matchday,
			right.matches_per_matchday,
			formatAverage
		),
		...(scorers ? [perUnit('goals')] : []),
		...(assists ? [perUnit('assists'), perUnit('contributions')] : []),
		perUnit('goals_conceded', true),
		...(scorers
			? [compareLine(t('compare.metric.goal_share'), left.goal_share, right.goal_share, formatRate)]
			: []),
		dayShare(t('compare.dayShare.titles'), (row) => row.titles),
		...(scorers ? [dayShare(t('compare.dayShare.topScorer'), (row) => row.top_scorer_days)] : []),
		...(assists ? [dayShare(t('compare.dayShare.topAssister'), (row) => row.top_assister_days)] : []),
		dayShare(t('compare.dayShare.mvp'), (row) => row.mvp_count)
	];
}

/**
 * @param {PlayerRow} left
 * @param {PlayerRow} right
 * @param {Tracking} tracking
 * @returns {CompareLine[]}
 */
export function duelLines(left, right, tracking) {
	const count = (/** @type {number|null} */ value) => String(value ?? 0);
	/**
	 * @param {'goals'|'assists'|'contributions'|'goals_conceded'} key
	 * @param {string} total
	 * @param {boolean} [lowerWins]
	 */
	const withPerMatch = (key, total, lowerWins = false) => [
		compareLine(total, unitValue(left, key, 'total'), unitValue(right, key, 'total'), count, lowerWins),
		compareLine(
			t(`compare.perUnit.${key}.match`),
			unitValue(left, key, 'match'),
			unitValue(right, key, 'match'),
			formatAverage,
			lowerWins
		)
	];
	return [
		compareLine(t('compare.metric.win_rate'), left.win_rate, right.win_rate, formatRate),
		compareLine(t('compare.duel.wins'), left.wins, right.wins, count),
		...(tracking.trackScorers ? withPerMatch('goals', t('compare.duel.goals')) : []),
		...(tracking.trackScorers && tracking.trackAssists
			? [
					...withPerMatch('assists', t('compare.duel.assists')),
					...withPerMatch('contributions', t('compare.duel.contributions'))
				]
			: []),
		...withPerMatch('goals_conceded', t('compare.duel.conceded'), true)
	];
}
