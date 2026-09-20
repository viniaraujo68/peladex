<script>
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   board: import('$lib/types.js').PairLeaderboard,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   playerHref?: (playerId: number) => string
	 * }}
	 */
	let { board, minDays, onMinDays, playerHref } = $props();

	const empty = $derived(board.together.length === 0);
</script>

<section class="card flex flex-col gap-4 bg-base-100 p-5">
	<div class="head">
		<div>
			<h3 class="font-semibold">{t('stats.pairs')}</h3>
			<p class="hint">{t('stats.pairsHint')}</p>
		</div>
		<label class="mindays">
			<span>{t('player.minDays')}</span>
			<input
				class="input input-sm"
				type="number"
				min="1"
				max="50"
				value={minDays}
				onchange={(e) => onMinDays(Number(e.currentTarget.value) || 1)}
			/>
		</label>
	</div>

	{#if empty}
		<p class="empty">{t('stats.pairsEmpty', { count: minDays })}</p>
	{:else}
		<div class="cols">
			{#each [{ rows: board.together, title: t('stats.pairsBest') }, { rows: board.apart, title: t('stats.pairsWorst') }] as column (column.title)}
				<div class="col">
					<h4 class="ctitle">{column.title}</h4>
					<div class="scroll">
						<table class="table table-sm">
							<thead>
								<tr>
									<th>{t('player.teammate')}</th>
									<th class="num">{t('player.days')}</th>
									<th class="num">{t('ranking.winRate')}</th>
									<th class="num">{t('player.delta')}</th>
								</tr>
							</thead>
							<tbody>
								{#each column.rows as row (row.player_a_id + '-' + row.player_b_id)}
									<tr>
										<td class="pair">
											{#if playerHref}
												<a class="link-hover" href={playerHref(row.player_a_id)}>{row.player_a}</a>
												<span class="amp">+</span>
												<a class="link-hover" href={playerHref(row.player_b_id)}>{row.player_b}</a>
											{:else}
												{row.player_a} <span class="amp">+</span> {row.player_b}
											{/if}
										</td>
										<td class="num muted">{row.days}</td>
										<td class="num">{formatRate(row.win_rate)}</td>
										<td class="num {rateClass(row.delta)}">{formatRateDelta(row.delta)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</section>

<style>
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
	}
	.hint {
		margin-top: 3px;
		max-width: 62ch;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.mindays {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.mindays input {
		width: 4.5rem;
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 16px;
	}
	.col {
		display: flex;
		flex-direction: column;
		gap: 6px;
		min-width: 0;
	}
	.ctitle {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-muted);
	}
	.scroll {
		overflow-x: auto;
	}
	.pair {
		white-space: nowrap;
		font-weight: 500;
	}
	.amp {
		margin: 0 2px;
		color: var(--ink-muted);
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.muted {
		color: var(--ink-muted);
	}
	.empty {
		padding: 20px 0;
		text-align: center;
		font-size: 0.86rem;
		color: var(--ink-muted);
	}
</style>
