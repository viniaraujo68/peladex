<script>
	import { t } from '$lib/i18n.svelte.js';
	import { UNITS, unitLabel } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import AssistNetwork from './AssistNetwork.svelte';
	import ChipGroup from './ChipGroup.svelte';
	import EvolutionChart from './EvolutionChart.svelte';
	import PairLeaderboard from './PairLeaderboard.svelte';

	/**
	 * @type {{
	 *   evolution: import('$lib/types.js').Evolution,
	 *   pairs: import('$lib/types.js').PairLeaderboard|null,
	 *   network: import('$lib/types.js').AssistNetwork|null,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   minMatchdays: number,
	 *   unit: import('$lib/metrics.js').Unit,
	 *   onUnit: (unit: import('$lib/metrics.js').Unit) => void,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { evolution, pairs, network, minDays, onMinDays, minMatchdays, unit, onUnit, playerHref } =
		$props();

	const tracking = getTracking();

	let metric = $state(/** @type {'win_rate'|'goals'|'assists'} */ ('win_rate'));

	const metrics = $derived(
		[
			{ id: 'win_rate', label: t('chart.metricRate'), on: true },
			{ id: 'goals', label: t('chart.metricGoals'), on: tracking.trackScorers },
			{
				id: 'assists',
				label: t('chart.metricAssists'),
				on: tracking.trackScorers && tracking.trackAssists
			}
		].filter((option) => option.on)
	);

	const unitOptions = $derived(UNITS.map((id) => ({ id, label: unitLabel(id) })));

	const title = $derived.by(() => {
		if (metric === 'win_rate') return t('stats.evolution');
		const name = metric === 'goals' ? t('chart.metricGoals') : t('chart.metricAssists');
		return unit === 'total'
			? `${name} · ${t('chart.cumulative')}`
			: `${name} · ${unitLabel(unit)} · ${t('chart.runningAverage')}`;
	});
</script>

<div class="flex flex-col gap-4">
	<div class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="charthead">
			<div>
				<h3 class="font-semibold">{title}</h3>
				{#if metric === 'win_rate' || unit !== 'total'}
					<p class="mt-1 text-xs text-base-content/65">
						{metric === 'win_rate' ? t('stats.evolutionHint') : t('chart.runningAverageHint')}
						{t('chart.defaultSeriesHint', { count: minMatchdays })}
					</p>
				{/if}
			</div>
			<div class="controls">
				<ChipGroup
					options={metrics}
					value={metric}
					label={t('chart.metric')}
					onchange={(id) => (metric = /** @type {any} */ (id))}
				/>
				{#if metric !== 'win_rate'}
					<ChipGroup
						options={unitOptions}
						value={unit}
						label={t('unit.label')}
						onchange={(id) => onUnit(/** @type {import('$lib/metrics.js').Unit} */ (id))}
					/>
				{/if}
			</div>
		</div>
		<EvolutionChart {evolution} {metric} {unit} {minMatchdays} />
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
	.controls {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 6px;
	}
	@media (max-width: 560px) {
		.controls {
			align-items: flex-start;
		}
	}
</style>
