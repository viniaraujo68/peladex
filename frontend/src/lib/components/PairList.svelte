<script>
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   rows: import('$lib/types.js').PairRow[],
	 *   title: string,
	 *   hint: string,
	 *   rateLabel: string,
	 *   peerLabel: string,
	 *   minDays: number,
	 *   playerHref?: (playerId: number) => string,
	 *   limit?: number
	 * }}
	 */
	let { rows, title, hint, rateLabel, peerLabel, minDays, playerHref, limit = 5 } = $props();

	let expanded = $state(false);
	const best = $derived(rows.slice(0, limit));
	const worst = $derived(rows.slice(-limit).reverse());
	const shown = $derived(expanded ? rows : [...best, ...worst.filter((r) => !best.includes(r))]);
</script>

<section class="card flex flex-col gap-3 bg-base-100 p-5">
	<div>
		<h3 class="font-semibold">{title}</h3>
		<p class="hint">{hint}</p>
	</div>

	{#if rows.length === 0}
		<p class="empty">{t('player.needMoreDays', { count: minDays })}</p>
	{:else}
		<div class="scroll">
			<table class="table table-sm">
				<thead>
					<tr>
						<th>{peerLabel}</th>
						<th class="num">{t('player.days')}</th>
						<th class="num">{rateLabel}</th>
						<th class="num">{t('player.delta')}</th>
					</tr>
				</thead>
				<tbody>
					{#each shown as row (row.player_id)}
						<tr>
							<td>
								{#if playerHref}
									<a class="link-hover font-medium" href={playerHref(row.player_id)}>{row.name}</a>
								{:else}
									<span class="font-medium">{row.name}</span>
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
		{#if rows.length > shown.length || expanded}
			<button type="button" class="btn btn-ghost btn-xs self-start" onclick={() => (expanded = !expanded)}>
				{expanded ? t('common.close') : t('common.all')} ({rows.length})
			</button>
		{/if}
	{/if}
</section>

<style>
	.hint {
		margin-top: 3px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.scroll {
		overflow-x: auto;
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
	:global(.rate-pos) {
		color: color-mix(in oklab, var(--color-success) 82%, var(--color-base-content));
		font-weight: 600;
	}
	:global(.rate-neg) {
		color: color-mix(in oklab, var(--color-error) 90%, var(--color-base-content));
		font-weight: 600;
	}
</style>
