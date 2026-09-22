<script>
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import AssistNetwork from './AssistNetwork.svelte';
	import EvolutionChart from './EvolutionChart.svelte';
	import PairLeaderboard from './PairLeaderboard.svelte';

	/**
	 * @type {{
	 *   evolution: import('$lib/types.js').Evolution,
	 *   pairs: import('$lib/types.js').PairLeaderboard|null,
	 *   network: import('$lib/types.js').AssistNetwork|null,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { evolution, pairs, network, minDays, onMinDays, playerHref } = $props();

	const tracking = getTracking();

	let metric = $state(/** @type {'win_rate'|'goals'|'assists'} */ ('win_rate'));

	const metrics = $derived([
		{ id: 'win_rate', label: t('chart.metricRate'), on: true },
		{ id: 'goals', label: t('chart.metricGoals'), on: tracking.trackScorers },
		{
			id: 'assists',
			label: t('chart.metricAssists'),
			on: tracking.trackScorers && tracking.trackAssists
		}
	]);
</script>

<div class="flex flex-col gap-4">
	<div class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="charthead">
			<div>
				<h3 class="font-semibold">
					{metric === 'win_rate'
						? t('stats.evolution')
						: `${metric === 'goals' ? t('chart.metricGoals') : t('chart.metricAssists')} · ${t('chart.cumulative')}`}
				</h3>
				{#if metric === 'win_rate'}
					<p class="mt-1 text-xs text-base-content/65">{t('stats.evolutionHint')}</p>
				{/if}
			</div>
			<div class="metrics" role="group" aria-label={t('chart.metric')}>
				{#each metrics as option (option.id)}
					{#if option.on}
						<button
							type="button"
							class="mchip"
							class:sel={metric === option.id}
							aria-pressed={metric === option.id}
							onclick={() => (metric = /** @type {any} */ (option.id))}
						>
							{option.label}
						</button>
					{/if}
				{/each}
			</div>
		</div>
		<EvolutionChart {evolution} {metric} />
	</div>

	{#if pairs}
		<PairLeaderboard board={pairs} {minDays} {onMinDays} {playerHref} />
	{/if}

	{#if network && tracking.trackScorers && tracking.trackAssists}
		<AssistNetwork {network} {playerHref} />
	{/if}
</div>

<style>
	.charthead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.metrics {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.mchip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.mchip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
</style>
