<script>
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import {
		UNITS,
		availableMetrics,
		formatMetric,
		isAverage,
		metricDetail,
		metricTitle,
		metricValue,
		rankRows,
		unitLabel
	} from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import ChipGroup from './ChipGroup.svelte';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   minMatchdays: number,
	 *   playerHref: (playerId: number) => string,
	 *   focus: import('$lib/metrics.js').MetricId|null,
	 *   unit: import('$lib/metrics.js').Unit,
	 *   onFocus: (id: import('$lib/metrics.js').MetricId|null) => void,
	 *   onUnit: (unit: import('$lib/metrics.js').Unit) => void
	 * }}
	 */
	let { ranking, minMatchdays, playerHref, focus, unit, onFocus, onUnit } = $props();

	const tracking = getTracking();

	const PREVIEW_COUNT = 5;

	let query = $state('');

	const metrics = $derived(availableMetrics(tracking));
	const focused = $derived(metrics.find((m) => m.id === focus) ?? null);
	const hasUnitMetric = $derived(metrics.some((m) => m.perUnit));

	const unitOptions = $derived(UNITS.map((id) => ({ id, label: unitLabel(id) })));
	const metricOptions = $derived(metrics.map((m) => ({ id: m.id, label: t(`metric.${m.id}`) })));

	const boards = $derived(
		metrics.map((metric) => {
			const { ranked, ranks } = rankRows(ranking, metric, unit, localeTag());
			const scoring = ranked
				.map((row, index) => ({ row, rank: ranks[index] }))
				.filter(({ row }) => (metricValue(row, metric, unit) ?? 0) > 0);
			const shown = scoring.slice(0, PREVIEW_COUNT);
			const last = shown.at(-1);
			const tiedOut = last ? scoring.slice(PREVIEW_COUNT).filter((e) => e.rank === last.rank).length : 0;
			return { metric, shown, tiedOut };
		})
	);

	const full = $derived.by(() => {
		if (!focused) return null;
		const { ranked, ranks, unranked } = rankRows(ranking, focused, unit, localeTag());
		const term = query.trim().toLowerCase();
		const matches = (/** @type {import('$lib/types.js').PlayerRow} */ row) =>
			!term || row.name.toLowerCase().includes(term);
		return {
			ranked: ranked
				.map((row, index) => ({ row, rank: ranks[index] }))
				.filter(({ row }) => matches(row)),
			unranked: unranked.filter(matches)
		};
	});

	/** @param {import('$lib/metrics.js').MetricId|null} id */
	function openFocus(id) {
		query = '';
		onFocus(id);
	}
</script>

{#snippet unitBar()}
	<ChipGroup
		options={unitOptions}
		value={unit}
		label={t('unit.label')}
		caption={t('unit.caption')}
		onchange={(id) => onUnit(/** @type {import('$lib/metrics.js').Unit} */ (id))}
	/>
{/snippet}

{#snippet qualifyNote()}
	<p class="note">{t('leaders.qualifyNote', { count: minMatchdays })}</p>
{/snippet}

{#if ranking.length === 0}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
		{t('ranking.empty')}
	</div>
{:else if focused && full}
	<div class="wrap">
		<div class="bar">
			<button type="button" class="btn btn-sm btn-ghost" onclick={() => openFocus(null)}>
				{t('leaders.back')}
			</button>
			<label class="input search">
				<Icon name="search" class="size-4 opacity-55" />
				<input placeholder={t('players.search')} bind:value={query} />
			</label>
		</div>
		<ChipGroup
			options={metricOptions}
			value={focused.id}
			label={t('players.sortBy')}
			onchange={(id) => onFocus(/** @type {import('$lib/metrics.js').MetricId} */ (id))}
		/>
		{#if focused.perUnit}{@render unitBar()}{/if}

		<section class="card bg-base-100 p-2 sm:p-4">
			<h3 class="ltitle px-2 pt-1">{metricTitle(focused, unit)}</h3>
			{#if full.ranked.length === 0 && full.unranked.length === 0}
				<p class="px-2 py-8 text-center text-base-content/65">
					{t('players.noResults', { query })}
				</p>
			{/if}
			<ol class="list">
				{#each full.ranked as entry (entry.row.player_id)}
					<li class="lrow">
						<span class="rank" data-top={entry.rank !== null && entry.rank <= 3}>
							{entry.rank}
						</span>
						<a class="lname link-hover" href={playerHref(entry.row.player_id)}>{entry.row.name}</a>
						<span class="ldetail">{metricDetail(entry.row, focused)}</span>
						<span class="lvalue">
							{formatMetric(metricValue(entry.row, focused, unit), focused, unit)}
						</span>
					</li>
				{/each}
			</ol>
			{#if full.unranked.length}
				<p class="divider-label">
					{focused.kind === 'note'
						? t('leaders.provisional')
						: t('leaders.fewDays', { count: minMatchdays })}
				</p>
				<ol class="list muted">
					{#each full.unranked as row (row.player_id)}
						<li class="lrow">
							<span class="rank">—</span>
							<a class="lname link-hover" href={playerHref(row.player_id)}>{row.name}</a>
							<span class="ldetail">{metricDetail(row, focused)}</span>
							<span class="lvalue">
								{formatMetric(metricValue(row, focused, unit), focused, unit)}
							</span>
						</li>
					{/each}
				</ol>
			{/if}
		</section>
		{#if isAverage(focused, unit)}{@render qualifyNote()}{/if}
	</div>
{:else}
	<div class="wrap">
		{#if hasUnitMetric}{@render unitBar()}{/if}
		<div class="board">
			{#each boards as board (board.metric.id)}
				<section class="card leader bg-base-100 p-4">
					<h3 class="ltitle">{metricTitle(board.metric, unit)}</h3>
					{#if board.shown.length === 0}
						<p class="lempty">{t('leaders.empty')}</p>
					{:else}
						<ol class="list">
							{#each board.shown as entry (entry.row.player_id)}
								<li class="lrow compact">
									<span class="rank" data-top={entry.rank !== null && entry.rank <= 3}>
										{entry.rank}
									</span>
									<a class="lname link-hover" href={playerHref(entry.row.player_id)}>
										{entry.row.name}
									</a>
									<span class="lvalue">
										{formatMetric(metricValue(entry.row, board.metric, unit), board.metric, unit)}
									</span>
								</li>
							{/each}
						</ol>
						{#if board.tiedOut > 0}
							<p class="tied">{t('leaders.tiedOut', { count: board.tiedOut })}</p>
						{/if}
					{/if}
					<button type="button" class="btn btn-sm btn-ghost more" onclick={() => openFocus(board.metric.id)}>
						{t('leaders.seeAll')}
					</button>
				</section>
			{/each}
		</div>
		{@render qualifyNote()}
	</div>
{/if}

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.search {
		max-width: 300px;
		flex: 1 1 200px;
	}
	.board {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 12px;
	}
	.leader {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.ltitle {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.list {
		display: flex;
		flex-direction: column;
	}
	.lrow {
		display: grid;
		grid-template-columns: 2.1em minmax(0, 1fr) auto auto;
		align-items: center;
		gap: 10px;
		padding: 7px 8px;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 7%, transparent);
	}
	.lrow:last-child {
		border-bottom: 0;
	}
	.lrow.compact {
		grid-template-columns: 1.8em minmax(0, 1fr) auto;
		padding: 5px 0;
	}
	.rank {
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		text-align: center;
		color: var(--ink-muted);
	}
	.rank[data-top='true'] {
		font-weight: 700;
		color: var(--ink-primary);
	}
	.lname {
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.ldetail {
		font-size: 0.72rem;
		color: var(--ink-muted);
		text-align: right;
	}
	.lvalue {
		min-width: 3.4em;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		text-align: right;
		color: var(--ink-primary);
	}
	.muted .lname,
	.muted .lvalue {
		color: var(--ink-muted);
		font-weight: 500;
	}
	.divider-label {
		margin: 10px 8px 2px;
		padding-top: 10px;
		border-top: 1px dashed color-mix(in oklch, var(--color-base-content) 18%, transparent);
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
	.lempty,
	.tied,
	.note {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.more {
		align-self: flex-start;
		margin-top: auto;
	}
	@media (max-width: 560px) {
		.lrow {
			grid-template-columns: 2.1em minmax(0, 1fr) auto;
		}
		.ldetail {
			grid-column: 2 / 4;
			grid-row: 2;
			text-align: left;
		}
	}
</style>
