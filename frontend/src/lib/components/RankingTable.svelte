<script>
	import { DataTable, sortRows, sortValue } from '@viniaraujo68/plinth/table';
	import { formatRate } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import {
		UNITS,
		formatMetric,
		isAverage,
		metricById,
		metricValue,
		rankValue,
		sharedRanks,
		unitLabel
	} from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import ChipGroup from './ChipGroup.svelte';
	import Icon from './Icon.svelte';

	const tracking = getTracking();

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   minMatchdays: number,
	 *   playerHref?: (playerId: number) => string,
	 *   unit: import('$lib/metrics.js').Unit,
	 *   onUnit: (unit: import('$lib/metrics.js').Unit) => void,
	 *   sort: import('@viniaraujo68/plinth/table').SortState,
	 *   onSort: (sort: import('@viniaraujo68/plinth/table').SortState) => void
	 * }}
	 */
	let { ranking, minMatchdays, playerHref, unit, onUnit, sort, onSort } = $props();

	/** @typedef {import('$lib/types.js').PlayerRow} Row */
	/** @typedef {import('$lib/metrics.js').MetricId} MetricId */

	const PODIUM = 3;
	const METRIC_COLUMNS = /** @type {MetricId[]} */ ([
		'win_rate',
		'goals',
		'assists',
		'contributions',
		'goal_share',
		'titles',
		'mvp_count',
		'matchdays',
		'rating'
	]);

	const showGoals = $derived(tracking.trackScorers);
	const showAssists = $derived(tracking.trackScorers && tracking.trackAssists);

	const unitOptions = $derived(UNITS.map((id) => ({ id, label: unitLabel(id) })));

	/** @param {string} key */
	const asMetric = (key) =>
		METRIC_COLUMNS.includes(/** @type {MetricId} */ (key))
			? metricById(/** @type {MetricId} */ (key))
			: null;

	/** @param {Row} r @param {number|null} value */
	const gated = (r, value) => (r.qualified ? value : null);

	/** @type {Record<string, (r: Row) => string>} */
	const text = $derived({
		recent_win_rate: (r) => formatRate(r.recent_win_rate),
		title_rate: (r) => formatRate(r.title_rate),
		presence: (r) => formatRate(r.presence),
		matches: (r) => String(r.matches),
		name: (r) => r.name
	});

	/** @param {string} key @param {Row} r */
	function display(key, r) {
		const metric = asMetric(key);
		if (metric) return formatMetric(metricValue(r, metric, unit), metric, unit);
		return (text[key] ?? text.name)(r);
	}

	/** @param {string} key @param {Row} r */
	function dimmed(key, r) {
		if (r.qualified) return false;
		const metric = asMetric(key);
		if (metric) return isAverage(metric, unit);
		return key === 'recent_win_rate' || key === 'title_rate';
	}

	/** @param {MetricId} id */
	function perUnitLabel(id) {
		const base = t(`ranking.${id}`);
		return unit === 'total' ? base : `${base}/${t(`unit.short.${unit}`)}`;
	}

	/** @param {MetricId} id @returns {(r: Row) => number|null} */
	const byMetric = (id) => (r) => rankValue(r, metricById(id), unit);

	/** @type {import('@viniaraujo68/plinth/table').Column<Row>[]} */
	const columns = $derived([
		{ key: 'rank', label: '#', sortable: false, align: 'center', class: 'w-12', cell: rankCell },
		{ key: 'name', label: t('ranking.player'), class: 'font-semibold', cell: nameCell },
		{
			key: 'win_rate',
			label: t('ranking.winRate'),
			numeric: true,
			sortBy: byMetric('win_rate'),
			cell: winRateCell
		},
		...(tracking.showRatings
			? [
					{
						key: 'rating',
						label: t('ranking.rating'),
						numeric: true,
						sortBy: byMetric('rating'),
						cell: ratingCell
					}
				]
			: []),
		{
			key: 'recent_win_rate',
			label: t('ranking.form'),
			numeric: true,
			sortBy: (/** @type {Row} */ r) => gated(r, r.recent_win_rate),
			cell: formCell
		},
		{ key: 'matchdays', label: t('ranking.matchdays'), numeric: true },
		{ key: 'matches', label: t('ranking.matches'), numeric: true },
		{ key: 'presence', label: t('ranking.presence'), numeric: true, cell: presenceCell },
		...(showGoals
			? [
					{
						key: 'goals',
						label: perUnitLabel('goals'),
						numeric: true,
						sortBy: byMetric('goals'),
						cell: goalsCell
					}
				]
			: []),
		...(showAssists
			? [
					{
						key: 'assists',
						label: perUnitLabel('assists'),
						numeric: true,
						sortBy: byMetric('assists'),
						cell: assistsCell
					},
					{
						key: 'contributions',
						label: perUnitLabel('contributions'),
						numeric: true,
						sortBy: byMetric('contributions'),
						cell: contributionsCell
					}
				]
			: []),
		...(showGoals
			? [
					{
						key: 'goal_share',
						label: t('ranking.goal_share'),
						numeric: true,
						sortBy: byMetric('goal_share'),
						cell: goalShareCell
					}
				]
			: []),
		{ key: 'titles', label: t('ranking.titles'), numeric: true },
		{
			key: 'title_rate',
			label: t('ranking.titleRate'),
			numeric: true,
			sortBy: (/** @type {Row} */ r) => gated(r, r.title_rate),
			cell: titleRateCell
		},
		{ key: 'mvp_count', label: t('ranking.mvp'), numeric: true }
	]);

	const activeColumn = $derived(columns.find((c) => c.key === sort.key) ?? columns[2]);

	const ranks = $derived.by(() => {
		const ordered = sortRows(ranking, activeColumn, sort.direction, localeTag());
		const positions = sharedRanks(ordered, (r) => sortValue(activeColumn, r));
		return new Map(ordered.map((r, i) => [r.player_id, positions[i]]));
	});

	const hasUnqualified = $derived(ranking.some((r) => !r.qualified));

	/** @param {Row} r */
	function tier(r) {
		const rank = ranks.get(r.player_id);
		return rank !== null && rank !== undefined && rank <= PODIUM ? String(rank) : undefined;
	}
</script>

{#snippet valueCell(/** @type {string} */ key, /** @type {Row} */ r)}
	{@const metric = asMetric(key)}
	<span class:dim={dimmed(key, r)}>
		{display(key, r)}
		{#if metric?.perUnit && unit !== 'total'}
			<small class="total">{metricValue(r, metric, 'total')}</small>
		{/if}
	</span>
{/snippet}

{#snippet rankCell(/** @type {Row} */ r)}
	<span class="rank" data-tier={tier(r)}>{ranks.get(r.player_id) ?? '—'}</span>
{/snippet}

{#snippet nameCell(/** @type {Row} */ r)}
	{#if playerHref}
		<a class="pname link-hover" class:dim={!r.qualified} href={playerHref(r.player_id)}>{r.name}</a>
	{:else}
		<span class="pname" class:dim={!r.qualified}>{r.name}</span>
	{/if}
{/snippet}

{#snippet winRateCell(/** @type {Row} */ r)}
	<span class="rate">{@render valueCell('win_rate', r)}</span>
{/snippet}

{#snippet ratingCell(/** @type {Row} */ r)}
	<span class:dim={metricValue(r, metricById('rating'), unit) === null}>
		{display('rating', r)}
	</span>
{/snippet}

{#snippet formCell(/** @type {Row} */ r)}
	{@render valueCell('recent_win_rate', r)}
{/snippet}

{#snippet presenceCell(/** @type {Row} */ r)}
	{@render valueCell('presence', r)}
{/snippet}

{#snippet goalsCell(/** @type {Row} */ r)}
	{@render valueCell('goals', r)}
{/snippet}

{#snippet assistsCell(/** @type {Row} */ r)}
	{@render valueCell('assists', r)}
{/snippet}

{#snippet contributionsCell(/** @type {Row} */ r)}
	{@render valueCell('contributions', r)}
{/snippet}

{#snippet goalShareCell(/** @type {Row} */ r)}
	{@render valueCell('goal_share', r)}
{/snippet}

{#snippet titleRateCell(/** @type {Row} */ r)}
	{@render valueCell('title_rate', r)}
{/snippet}

{#snippet playerCard(/** @type {Row} */ r)}
	<div class="rcard">
		<span class="rank rc-rank" data-tier={tier(r)}>{ranks.get(r.player_id) ?? '—'}</span>
		<div class="rc-mid">
			<span class="rc-name" class:dim={!r.qualified}>
				{#if playerHref}
					<a class="link-hover" href={playerHref(r.player_id)}>{r.name}</a>
				{:else}
					{r.name}
				{/if}
				{#if r.mvp_count > 0}
					<span class="rc-mvp" title={t('ranking.mvp')}>
						<Icon name="star" class="size-3" />{r.mvp_count}
					</span>
				{/if}
			</span>
			<span class="rc-sub">
				{t('ranking.cardSub', {
					count: r.matchdays,
					matches: r.matches,
					goals: showAssists
						? `${r.goals}G ${r.assists}A`
						: t('ranking.goalCount', { count: r.goals })
				})}
			</span>
		</div>
		<span class="rc-value">
			<span class="rc-rate" class:dim={dimmed(activeColumn.key, r)}>
				{display(activeColumn.key === 'name' ? 'win_rate' : activeColumn.key, r)}
			</span>
			<span class="rc-label">
				{activeColumn.key === 'name' ? t('ranking.winRate') : activeColumn.label}
			</span>
		</span>
	</div>
{/snippet}

{#if ranking.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('ranking.empty')}</div>
{:else}
	<div class="ranking">
		{#if showGoals}
			<ChipGroup
				options={unitOptions}
				value={unit}
				label={t('unit.label')}
				caption={t('unit.caption')}
				onchange={(id) => onUnit(/** @type {import('$lib/metrics.js').Unit} */ (id))}
			/>
		{/if}
		<DataTable
			rows={ranking}
			{columns}
			rowKey={(r) => r.player_id}
			bind:sort={() => sort, (value) => value && onSort(value)}
			locale={localeTag()}
			label={t('tab.ranking')}
			sortLabel={(column) => t('ranking.sortByColumn', { column: column.label })}
			card={playerCard}
		/>
		{#if hasUnqualified}
			<p class="note">{t('leaders.qualifyNote', { count: minMatchdays })}</p>
		{/if}
	</div>
{/if}

<style>
	.ranking {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.ranking :global(.table) {
		--table-ink-muted: var(--ink-muted);
	}
	.rank {
		display: inline-grid;
		place-items: center;
		min-width: 1.55em;
		min-height: 1.55em;
		padding: 0 0.3em;
		border-radius: 999px;
		font-size: 0.95rem;
		font-variant-numeric: tabular-nums;
		line-height: 1;
		color: var(--ink-muted);
	}
	.rank[data-tier] {
		font-weight: 700;
		color: var(--ink-primary);
		box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--color-primary) 32%, transparent);
	}
	.rank[data-tier='2'] {
		background: color-mix(in oklch, var(--color-primary) 15%, transparent);
	}
	.rank[data-tier='1'] {
		background: var(--color-primary);
		color: var(--color-primary-content);
		box-shadow: none;
	}
	.pname {
		overflow-wrap: anywhere;
	}
	.rate {
		font-weight: 600;
		color: var(--ink-primary);
	}
	.dim {
		color: var(--ink-muted);
		font-weight: 400;
	}
	.total {
		margin-left: 4px;
		font-size: 0.7em;
		color: var(--ink-muted);
	}
	.note {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.rcard {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.rc-rank {
		flex: none;
		font-size: 1rem;
	}
	.rc-mid {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
		flex: 1;
	}
	.rc-name {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-weight: 700;
		overflow-wrap: anywhere;
	}
	.rc-mvp {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--ink-primary);
	}
	.rc-sub {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.rc-value {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 1px;
	}
	.rc-rate {
		font-size: 1.05rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--ink-primary);
	}
	.rc-rate.dim {
		color: var(--ink-muted);
		font-weight: 500;
	}
	.rc-label {
		font-size: 0.66rem;
		color: var(--ink-muted);
		white-space: nowrap;
	}
</style>
