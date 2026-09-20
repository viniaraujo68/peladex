<script>
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   rows: import('$lib/types.js').PairRow[],
	 *   title: string,
	 *   hint: string,
	 *   rateLabel: string,
	 *   rateWithoutLabel: string,
	 *   peerLabel: string,
	 *   minDays: number,
	 *   playerHref?: (playerId: number) => string,
	 *   limit?: number
	 * }}
	 */
	let {
		rows,
		title,
		hint,
		rateLabel,
		rateWithoutLabel,
		peerLabel,
		minDays,
		playerHref,
		limit = 6
	} = $props();

	let expanded = $state(false);

	const comparable = $derived(rows.filter((r) => r.delta !== null));
	const shown = $derived.by(() => {
		if (expanded) return rows;
		const best = comparable.slice(0, limit);
		const worst = comparable.slice(-limit).filter((r) => !best.includes(r));
		const rest = rows.filter((r) => r.delta === null).slice(0, 3);
		return [...best, ...worst.reverse(), ...rest];
	});
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
						<th class="num">{rateWithoutLabel}</th>
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
							<td class="num muted">
								{#if row.win_rate_without === null}
									<span title={t('player.neverApart')}>—</span>
								{:else}
									{formatRate(row.win_rate_without)}
									<span class="sub">({row.days_without})</span>
								{/if}
							</td>
							<td class="num {row.delta === null ? 'muted' : rateClass(row.delta)}">
								{#if row.delta === null}
									<span title={t('player.neverApart')}>—</span>
								{:else}
									{formatRateDelta(row.delta)}
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if rows.length > shown.length || expanded}
			<button
				type="button"
				class="btn btn-ghost btn-xs self-start"
				onclick={() => (expanded = !expanded)}
			>
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
		white-space: nowrap;
	}
	.muted {
		color: var(--ink-muted);
	}
	.sub {
		font-size: 0.72em;
		opacity: 0.75;
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
