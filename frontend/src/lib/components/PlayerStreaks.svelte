<script>
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { sharedRanks } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   minMatchdays: number,
	 *   playerHref: (playerId: number) => string,
	 *   focus: string|null,
	 *   onFocus: (id: string|null) => void
	 * }}
	 */
	let { ranking, minMatchdays, playerHref, focus, onFocus } = $props();

	/** @typedef {import('$lib/types.js').PlayerRow} Row */

	const tracking = getTracking();

	const PREVIEW_COUNT = 5;

	let query = $state('');

	/**
	 * @param {(row: Row) => number} value
	 * @param {(row: Row) => boolean} eligible
	 */
	function ordered(value, eligible) {
		const rows = ranking
			.filter((row) => eligible(row) && value(row) > 0)
			.sort(
				(a, b) =>
					value(b) - value(a) || b.matches - a.matches || a.name.localeCompare(b.name, localeTag())
			);
		const ranks = sharedRanks(rows, value);
		return rows.map((row, index) => ({ row, count: value(row), rank: ranks[index] }));
	}

	/**
	 * @param {(row: Row) => number} value
	 * @param {(row: Row) => boolean} [eligible]
	 */
	function streak(value, eligible = () => true) {
		const all = ordered(value, eligible);
		return { rows: all.slice(0, PREVIEW_COUNT), all: () => all };
	}

	const boards = $derived(
		[
			tracking.trackScorers && {
				id: 'scoring',
				title: t('streaks.scoring'),
				hint: t('streaks.scoringHint'),
				unit: 'streaks.inARow',
				...streak((r) => r.goal_streak)
			},
			tracking.trackScorers && {
				id: 'drought',
				title: t('streaks.drought'),
				hint: t('streaks.droughtHint'),
				unit: 'streaks.withoutScoring',
				...streak(
					(r) => r.goal_drought,
					(r) => r.goals > 0
				)
			},
			{
				id: 'titles',
				title: t('streaks.titles'),
				hint: t('streaks.titlesHint'),
				unit: 'streaks.inARow',
				...streak((r) => r.title_streak)
			},
			{
				id: 'presence',
				title: t('streaks.presence'),
				hint: t('streaks.presenceHint'),
				unit: 'streaks.inARow',
				...streak((r) => r.presence_streak)
			},
			{
				id: 'missing',
				title: t('streaks.missing'),
				hint: t('streaks.missingHint', { count: minMatchdays }),
				unit: 'streaks.away',
				...streak(
					(r) => r.absent_matchdays,
					(r) => r.matchdays >= minMatchdays
				)
			}
		].filter((board) => !!board)
	);

	const hasAny = $derived(boards.some((board) => board && board.rows.length > 0));

	const focused = $derived(
		boards.find((board) => board && `streak-${board.id}` === focus) ?? null
	);

	const full = $derived.by(() => {
		if (!focused) return [];
		const term = query.trim().toLowerCase();
		return focused.all().filter(({ row }) => !term || row.name.toLowerCase().includes(term));
	});

	/** @param {string|null} id */
	function openFocus(id) {
		query = '';
		onFocus(id);
	}
</script>

{#if focused}
	<section class="flex flex-col gap-3">
		<div class="bar">
			<button type="button" class="btn btn-sm btn-ghost" onclick={() => openFocus(null)}>
				{t('streaks.back')}
			</button>
			<label class="input search">
				<Icon name="search" class="size-4 opacity-55" />
				<input placeholder={t('players.search')} bind:value={query} />
			</label>
		</div>
		<div class="card streak bg-base-100 p-4">
			<span class="stitle">{focused.title}</span>
			<span class="hint">{focused.hint}</span>
			{#if full.length === 0}
				<p class="hint mt-3">{query ? t('players.noResults', { query }) : t('streaks.nobody')}</p>
			{:else}
				<ol class="list mt-2">
					{#each full as entry (entry.row.player_id)}
						<li class="srow">
							<span class="srank">{entry.rank}</span>
							<a class="sname link-hover" href={playerHref(entry.row.player_id)}>
								{entry.row.name}
							</a>
							<span class="svalue">{t(focused.unit, { count: entry.count })}</span>
						</li>
					{/each}
				</ol>
			{/if}
		</div>
	</section>
{:else if hasAny}
	<section class="flex flex-col gap-3">
		<div>
			<h3 class="font-semibold">{t('streaks.title')}</h3>
			<p class="hint">{t('streaks.hint')}</p>
		</div>
		<div class="board">
			{#each boards as board (board && board.id)}
				{#if board}
					<div class="card streak bg-base-100 p-4">
						<span class="stitle">{board.title}</span>
						<span class="hint">{board.hint}</span>
						{#if board.rows.length === 0}
							<p class="hint">{t('streaks.nobody')}</p>
						{:else}
							<ol class="list">
								{#each board.rows as entry (entry.row.player_id)}
									<li class="srow">
										<a class="sname link-hover" href={playerHref(entry.row.player_id)}>
											{entry.row.name}
										</a>
										<span class="svalue">{t(board.unit, { count: entry.count })}</span>
									</li>
								{/each}
							</ol>
						{/if}
						<button
							type="button"
							class="btn btn-sm btn-ghost more"
							onclick={() => openFocus(`streak-${board.id}`)}
						>
							{t('leaders.seeAll')}
						</button>
					</div>
				{/if}
			{/each}
		</div>
	</section>
{/if}

<style>
	.board {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
		gap: 12px;
	}
	.streak {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.stitle {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.hint {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.list {
		display: flex;
		flex-direction: column;
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
	.more {
		align-self: flex-start;
		margin-top: auto;
	}
	.srank {
		min-width: 1.8em;
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		color: var(--ink-muted);
	}
	.srow {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 8px;
		padding: 5px 0;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 7%, transparent);
	}
	.srow:last-child {
		border-bottom: 0;
	}
	.sname {
		flex: 1;
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.svalue {
		flex: none;
		font-size: 0.8rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--ink-primary);
	}
</style>
