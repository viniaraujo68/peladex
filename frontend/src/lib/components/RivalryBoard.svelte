<script>
	import { formatRate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import BoardCard from './BoardCard.svelte';
	import CompareButton from './CompareButton.svelte';
	import MinDaysField from './MinDaysField.svelte';

	/**
	 * @type {{
	 *   board: import('$lib/types.js').RivalryBoard,
	 *   onMinDays: (value: number) => void,
	 *   playerHref: (playerId: number) => string,
	 *   onCompare: (sides: { a: number[], b: number[] }) => void
	 * }}
	 */
	let { board, onMinDays, playerHref, onCompare } = $props();

	/** @typedef {'lopsided'|'classics'|'balanced'} ListId */

	let list = $state(/** @type {ListId} */ ('lopsided'));

	const options = $derived([
		{ id: 'lopsided', label: t('rivalry.lopsided') },
		{ id: 'classics', label: t('rivalry.classics') },
		{ id: 'balanced', label: t('rivalry.balanced') }
	]);

	const isLopsided = $derived(list === 'lopsided');
	const empty = $derived(board[list].length ? null : t('rivalry.empty', { count: board.min_days }));
</script>

<BoardCard
	title={t('rivalry.title')}
	{options}
	value={list}
	onchange={(id) => (list = /** @type {ListId} */ (id))}
	{empty}
>
	{#snippet controls()}
		<MinDaysField value={board.min_days} onchange={onMinDays} />
	{/snippet}
	<thead>
		<tr>
			<th>{t('rivalry.players')}</th>
			<th class="text-right">{isLopsided ? t('player.days') : t('rivalry.matches')}</th>
			<th class="text-right">{t('rivalry.record')}</th>
			{#if isLopsided}<th class="text-right">{t('ranking.winRate')}</th>{/if}
			<th><span class="sr-only">{t('compare.view')}</span></th>
		</tr>
	</thead>
	<tbody>
		{#each board[list] as row (row.leader_id + '-' + row.trailer_id)}
			<tr>
				<td class="font-medium whitespace-nowrap">
					<a class="link-hover font-bold" href={playerHref(row.leader_id)}>{row.leader}</a>
					<span class="sep">x</span>
					<a class="link-hover" href={playerHref(row.trailer_id)}>{row.trailer}</a>
				</td>
				<td class="text-right tabular-nums text-[var(--ink-muted)]">
					{isLopsided ? row.days : row.matches}
				</td>
				<td class="record text-right tabular-nums whitespace-nowrap">
					<span class="w">{row.wins}</span>-<span>{row.draws}</span>-<span class="l">{row.losses}</span>
				</td>
				{#if isLopsided}<td class="text-right tabular-nums">{formatRate(row.win_rate)}</td>{/if}
				<td class="text-right">
					<CompareButton
						label={t('rivalry.compareLabel', { a: row.leader, b: row.trailer })}
						onclick={() => onCompare({ a: [row.leader_id], b: [row.trailer_id] })}
					/>
				</td>
			</tr>
		{/each}
	</tbody>
</BoardCard>

<style>
	.sep {
		margin: 0 4px;
		color: var(--ink-muted);
	}
	.record {
		color: var(--ink-muted);
	}
	.record .w {
		font-weight: 700;
		color: var(--ink-primary);
	}
	.record .l {
		color: var(--color-error);
	}
</style>
