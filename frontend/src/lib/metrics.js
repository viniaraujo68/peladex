import { competitionRanks } from '@viniaraujo68/plinth/table';
import { formatAverage, formatNote, formatRate } from './format.svelte.js';
import { t } from './i18n.svelte.js';

/** @typedef {import('./types.js').PlayerRow} PlayerRow */
/** @typedef {'total'|'match'|'day'} Unit */
/**
 * @typedef {'win_rate'|'goals'|'assists'|'contributions'|'goal_share'|'assist_share'
 *   |'top_scorer_days'|'top_assister_days'|'top_contributor_days'
 *   |'titles'|'mvp_count'|'matchdays'|'matches_per_matchday'|'matches'|'rating'} MetricId
 */
/**
 * @typedef {object} Metric
 * @property {MetricId} id
 * @property {'rate'|'count'|'ratio'|'note'} kind
 * @property {boolean} perUnit
 * @property {'scorers'|'assists'|'ratings'|null} needs
 */

/** @type {Unit[]} */
export const UNITS = ['total', 'match', 'day'];
/** @type {Unit} */
export const DEFAULT_UNIT = 'match';

/** @type {Record<'goals'|'assists'|'contributions', Record<Unit, keyof PlayerRow>>} */
const UNIT_FIELDS = {
	goals: { total: 'goals', match: 'goals_per_match', day: 'goals_per_matchday' },
	assists: { total: 'assists', match: 'assists_per_match', day: 'assists_per_matchday' },
	contributions: {
		total: 'contributions',
		match: 'contributions_per_match',
		day: 'contributions_per_matchday'
	}
};

/** @type {Metric[]} */
export const METRICS = [
	{ id: 'win_rate', kind: 'rate', perUnit: false, needs: null },
	{ id: 'goals', kind: 'count', perUnit: true, needs: 'scorers' },
	{ id: 'assists', kind: 'count', perUnit: true, needs: 'assists' },
	{ id: 'contributions', kind: 'count', perUnit: true, needs: 'assists' },
	{ id: 'top_scorer_days', kind: 'count', perUnit: false, needs: 'scorers' },
	{ id: 'top_assister_days', kind: 'count', perUnit: false, needs: 'assists' },
	{ id: 'top_contributor_days', kind: 'count', perUnit: false, needs: 'assists' },
	{ id: 'goal_share', kind: 'rate', perUnit: false, needs: 'scorers' },
	{ id: 'assist_share', kind: 'rate', perUnit: false, needs: 'assists' },
	{ id: 'titles', kind: 'count', perUnit: false, needs: null },
	{ id: 'mvp_count', kind: 'count', perUnit: false, needs: null },
	{ id: 'matchdays', kind: 'count', perUnit: false, needs: null },
	{ id: 'matches_per_matchday', kind: 'ratio', perUnit: false, needs: null },
	{ id: 'matches', kind: 'count', perUnit: false, needs: null },
	{ id: 'rating', kind: 'note', perUnit: false, needs: 'ratings' }
];

/** @param {string|null|undefined} value @returns {Unit} */
export function parseUnit(value) {
	return UNITS.includes(/** @type {Unit} */ (value)) ? /** @type {Unit} */ (value) : DEFAULT_UNIT;
}

/** @param {import('./tracking.svelte.js').Tracking} tracking */
export function availableMetrics(tracking) {
	return METRICS.filter((metric) => {
		if (metric.needs === 'scorers') return tracking.trackScorers;
		if (metric.needs === 'assists') return tracking.trackScorers && tracking.trackAssists;
		if (metric.needs === 'ratings') return tracking.showRatings;
		return true;
	});
}

/** @param {MetricId} id */
export function metricById(id) {
	return METRICS.find((metric) => metric.id === id) ?? METRICS[0];
}

/** @param {Metric} metric @param {Unit} unit */
export function isAverage(metric, unit) {
	return metric.kind === 'rate' || metric.kind === 'ratio' || (metric.perUnit && unit !== 'total');
}

/** @param {PlayerRow} row @param {Metric} metric @param {Unit} unit @returns {number|null} */
export function metricValue(row, metric, unit) {
	if (metric.id === 'rating') return row.rating_provisional ? null : row.rating;
	if (metric.perUnit) {
		const field = UNIT_FIELDS[/** @type {'goals'|'assists'|'contributions'} */ (metric.id)][unit];
		return /** @type {number} */ (row[field]);
	}
	return /** @type {number|null} */ (row[metric.id]);
}

/** @param {PlayerRow} row @param {Metric} metric @param {Unit} unit */
export function rankValue(row, metric, unit) {
	if (isAverage(metric, unit) && !row.qualified) return null;
	return metricValue(row, metric, unit);
}

/** @param {number|null} value @param {Metric} metric @param {Unit} unit */
export function formatMetric(value, metric, unit) {
	if (metric.kind === 'rate') return formatRate(value);
	if (metric.kind === 'note') return formatNote(value);
	if (metric.kind === 'ratio') return formatAverage(value);
	if (value === null || value === undefined) return '—';
	return metric.perUnit && unit !== 'total' ? formatAverage(value) : String(value);
}

/** @param {Metric} metric @param {Unit} unit */
export function metricTitle(metric, unit) {
	return t(`metric.${metric.id}`) + (metric.perUnit ? ` · ${unitLabel(unit)}` : '');
}

/** @type {MetricId[]} */
export const MATCH_VARIANTS = ['matches_per_matchday', 'matches'];

/** @param {import('./tracking.svelte.js').Tracking} tracking */
export function unitCaption(tracking) {
	return tracking.trackAssists ? t('unit.captionBoth') : t('unit.captionGoals');
}

export function unitOptions() {
	return UNITS.map((id) => ({ id, label: unitLabel(id) }));
}

/** @param {Unit} unit */
export function unitLabel(unit) {
	return t(`unit.${unit}`);
}

/** @param {PlayerRow} row @param {Metric} metric */
export function metricDetail(row, metric) {
	if (metric.id === 'win_rate') {
		return t('metric.detailRate', { wins: row.wins, draws: row.draws, losses: row.losses });
	}
	if (metric.id === 'goal_share') {
		return t('metric.detailShare', { value: row.goals, total: row.team_goals });
	}
	if (metric.id === 'assist_share') {
		return t('metric.detailShare', { value: row.assists, total: row.team_goals });
	}
	if (metric.perUnit) {
		const total = /** @type {number} */ (row[UNIT_FIELDS[/** @type {'goals'} */ (metric.id)].total]);
		return t(`metric.detail.${metric.id}`, { count: total, matches: row.matches, days: row.matchdays });
	}
	if (
		metric.id === 'top_scorer_days' ||
		metric.id === 'top_assister_days' ||
		metric.id === 'top_contributor_days'
	) {
		return t('metric.detailDayLeader', { count: row[metric.id], days: row.matchdays });
	}
	if (metric.id === 'titles') {
		return t('metric.detailTitles', { rate: formatRate(row.title_rate), days: row.matchdays });
	}
	if (metric.id === 'matchdays') return t('metric.detailPresence', { rate: formatRate(row.presence) });
	if (metric.id === 'matches_per_matchday' || metric.id === 'matches') {
		return t('metric.detailMatches', { count: row.matches, days: row.matchdays });
	}
	return t('metric.detailDays', { count: row.matchdays });
}

/** @param {import('./types.js').FormEntry[]} form */
export function formScore(form) {
	return form.reduce(
		(sum, entry) => sum + entry.teams - entry.position + (entry.champion ? 1 : 0),
		0
	);
}

/**
 * @param {PlayerRow[]} rows
 * @param {Metric} metric
 * @param {Unit} unit
 * @param {string} locale
 */
export function rankRows(rows, metric, unit, locale) {
	const byName = (/** @type {PlayerRow} */ a, /** @type {PlayerRow} */ b) =>
		a.name.localeCompare(b.name, locale);
	const ranked = rows.filter((row) => rankValue(row, metric, unit) !== null);
	const unranked = rows.filter((row) => rankValue(row, metric, unit) === null);
	const value = (/** @type {PlayerRow} */ row) => metricValue(row, metric, unit) ?? -1;
	ranked.sort((a, b) => value(b) - value(a) || b.matches - a.matches || byName(a, b));
	unranked.sort((a, b) => value(b) - value(a) || b.matches - a.matches || byName(a, b));
	return {
		ranked,
		ranks: competitionRanks(ranked, (row) => rankValue(row, metric, unit), locale),
		unranked
	};
}
