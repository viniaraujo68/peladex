<script>
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import BoardCard from './BoardCard.svelte';
	import CompareButton from './CompareButton.svelte';
	import MinDaysField from './MinDaysField.svelte';

	/**
	 * @type {{
	 *   board: import('$lib/types.js').PairLeaderboard,
	 *   onMinDays: (value: number) => void,
	 *   playerHref: (playerId: number) => string,
	 *   onCompare: (sides: { a: number[], b: number[] }) => void
	 * }}
	 */
	let { board, onMinDays, playerHref, onCompare } = $props();

	const tracking = getTracking();
	const showAssists = $derived(tracking.trackScorers && tracking.trackAssists);

	/** @typedef {'together'|'apart'|'assists'} ListId */

	let list = $state(/** @type {ListId} */ ('together'));
	const shown = $derived(list === 'assists' && !showAssists ? 'together' : list);

	const options = $derived([
		{ id: 'together', label: t('stats.pairsBest') },
		{ id: 'apart', label: t('stats.pairsWorst') },
		...(showAssists ? [{ id: 'assists', label: t('stats.pairsAssists') }] : [])
	]);

	const empty = $derived.by(() => {
		if (shown === 'assists') return board.assists.length ? null : t('stats.assistsEmpty');
		return board[shown].length ? null : t('stats.pairsEmpty', { count: board.min_days });
	});
</script>

{#snippet player(/** @type {number} */ id, /** @type {string} */ name)}
	<a class="link-hover" href={playerHref(id)}>{name}</a>
{/snippet}

<BoardCard
	title={t('stats.pairs')}
	{options}
	value={shown}
	onchange={(id) => (list = /** @type {ListId} */ (id))}
	{empty}
>
	{#snippet controls()}
		{#if shown !== 'assists'}<MinDaysField value={board.min_days} onchange={onMinDays} />{/if}
	{/snippet}
	{#if shown === 'assists'}
		<thead>
			<tr>
				<th>{t('stats.pairColumn')}</th>
				<th class="text-right">{t('ranking.assists')}</th>
				<th><span class="sr-only">{t('compare.view')}</span></th>
			</tr>
		</thead>
		<tbody>
			{#each board.assists as link (link.assist_player_id + '-' + link.scorer_player_id)}
				<tr>
					<td class="font-medium whitespace-nowrap">
						{@render player(link.assist_player_id, link.assist_name)}
						<span class="sep">&rarr;</span>
						{@render player(link.scorer_player_id, link.scorer_name)}
					</td>
					<td class="text-right font-bold tabular-nums">{link.goals}</td>
					<td class="text-right">
						<CompareButton
							label={t('stats.pairsCompareLabel', { a: link.assist_name, b: link.scorer_name })}
							onclick={() => onCompare({ a: [link.assist_player_id, link.scorer_player_id], b: [] })}
						/>
					</td>
				</tr>
			{/each}
		</tbody>
	{:else}
		<thead>
			<tr>
				<th>{t('stats.pairColumn')}</th>
				<th class="text-right">{t('player.days')}</th>
				<th class="text-right">{t('stats.pairRate')}</th>
				<th class="text-right">{t('stats.pairExpected')}</th>
				<th class="text-right">{t('player.delta')}</th>
				{#if showAssists}<th class="text-right">{t('stats.pairAssists')}</th>{/if}
				<th><span class="sr-only">{t('compare.view')}</span></th>
			</tr>
		</thead>
		<tbody>
			{#each board[shown] as row (row.player_a_id + '-' + row.player_b_id)}
				<tr>
					<td class="font-medium whitespace-nowrap">
						{@render player(row.player_a_id, row.player_a)}
						<span class="sep">+</span>
						{@render player(row.player_b_id, row.player_b)}
					</td>
					<td class="text-right tabular-nums text-[var(--ink-muted)]">{row.days}</td>
					<td class="text-right tabular-nums">{formatRate(row.win_rate)}</td>
					<td class="text-right tabular-nums text-[var(--ink-muted)]">{formatRate(row.expected)}</td>
					<td class="text-right tabular-nums {rateClass(row.delta)}">{formatRateDelta(row.delta)}</td>
					{#if showAssists}
						<td
							class="text-right tabular-nums whitespace-nowrap"
							title={t('stats.pairAssistsSplit', {
								a: row.player_a,
								b: row.player_b,
								ab: row.assists_a_to_b,
								ba: row.assists_b_to_a
							})}
						>
							{row.assists_a_to_b}<span class="sep">⇄</span>{row.assists_b_to_a}
						</td>
					{/if}
					<td class="text-right">
						<CompareButton
							label={t('stats.pairsCompareLabel', { a: row.player_a, b: row.player_b })}
							onclick={() => onCompare({ a: [row.player_a_id, row.player_b_id], b: [] })}
						/>
					</td>
				</tr>
			{/each}
		</tbody>
	{/if}
</BoardCard>

<style>
	.sep {
		margin: 0 4px;
		color: var(--ink-muted);
	}
</style>
