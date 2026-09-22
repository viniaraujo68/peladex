<script>
	import { DataTable } from '@viniaraujo68/plinth/table';
	import { formatNote, formatRate } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import Icon from './Icon.svelte';

	const tracking = getTracking();

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   playerHref?: (playerId: number) => string
	 * }}
	 */
	let { ranking, playerHref } = $props();

	/** @typedef {import('$lib/types.js').PlayerRow} Row */

	const PODIUM = 3;

	/** @type {import('@viniaraujo68/plinth/table').SortState} */
	let sort = $state({ key: 'win_rate', direction: 'desc' });

	const showGoals = $derived(tracking.trackScorers);
	const showAssists = $derived(tracking.trackScorers && tracking.trackAssists);

	/** @param {Row} r */
	const ratingValue = (r) => (r.rating_provisional ? null : r.rating);

	/** @type {import('@viniaraujo68/plinth/table').Column<Row>[]} */
	const columns = $derived([
		{ key: 'rank', label: '#', sortable: false, align: 'center', class: 'w-12', cell: rankCell },
		{ key: 'name', label: t('ranking.player'), class: 'font-semibold', cell: nameCell },
		{ key: 'win_rate', label: t('ranking.winRate'), numeric: true, cell: rateCell },
		...(tracking.showRatings
			? [
					{
						key: 'rating',
						label: t('ranking.rating'),
						numeric: true,
						sortBy: ratingValue,
						cell: ratingCell
					}
				]
			: []),
		{ key: 'recent_win_rate', label: t('ranking.form'), numeric: true, cell: formCell },
		{ key: 'matchdays', label: t('ranking.matchdays'), numeric: true },
		{ key: 'presence', label: t('ranking.presence'), numeric: true, cell: presenceCell },
		...(showGoals ? [{ key: 'goals', label: t('ranking.goals'), numeric: true }] : []),
		...(showAssists
			? [{ key: 'assists', label: t('ranking.assists'), numeric: true }]
			: []),
		{ key: 'titles', label: t('ranking.titles'), numeric: true },
		{ key: 'title_rate', label: t('ranking.titleRate'), numeric: true, cell: titleRateCell },
		{ key: 'mvp_count', label: t('ranking.mvp'), numeric: true }
	]);

	/** @param {number} index */
	const tier = (index) => (index < PODIUM ? String(index + 1) : undefined);
</script>

{#snippet rankCell(/** @type {Row} */ _r, /** @type {number} */ index)}
	<span class="rank" data-tier={tier(index)}>{index + 1}</span>
{/snippet}

{#snippet nameCell(/** @type {Row} */ r)}
	{#if playerHref}
		<a class="pname link-hover" href={playerHref(r.player_id)}>{r.name}</a>
	{:else}
		<span class="pname">{r.name}</span>
	{/if}
{/snippet}

{#snippet rateCell(/** @type {Row} */ r)}
	<span class="rate">{formatRate(r.win_rate)}</span>
{/snippet}

{#snippet ratingCell(/** @type {Row} */ r)}
	<span class={ratingValue(r) === null ? 'text-base-content/50' : ''}>
		{formatNote(ratingValue(r))}
	</span>
{/snippet}

{#snippet formCell(/** @type {Row} */ r)}
	<span class={r.recent_win_rate === null ? 'text-base-content/50' : ''}>
		{formatRate(r.recent_win_rate)}
	</span>
{/snippet}

{#snippet presenceCell(/** @type {Row} */ r)}
	<span>{formatRate(r.presence)}</span>
{/snippet}

{#snippet titleRateCell(/** @type {Row} */ r)}
	<span>{formatRate(r.title_rate)}</span>
{/snippet}

{#snippet playerCard(/** @type {Row} */ r, /** @type {number} */ index)}
	<div class="rcard">
		<span class="rank rc-rank" data-tier={tier(index)}>{index + 1}</span>
		<div class="rc-mid">
			<span class="rc-name">
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
		<span class="rc-rate">{formatRate(r.win_rate)}</span>
	</div>
{/snippet}

{#if ranking.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('ranking.empty')}</div>
{:else}
	<div class="ranking">
		<DataTable
			rows={ranking}
			{columns}
			rowKey={(r) => r.player_id}
			bind:sort
			locale={localeTag()}
			label={t('tab.ranking')}
			sortLabel={(column) => t('ranking.sortByColumn', { column: column.label })}
			card={playerCard}
		/>
	</div>
{/if}

<style>
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
	.rc-rate {
		font-size: 1.05rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--ink-primary);
	}
</style>
