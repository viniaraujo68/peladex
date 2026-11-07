<script>
	import { SINGLE_GAME_UNITS, getDayTypeView, visibleUnit } from '$lib/dayType.js';
	import { SegmentedControl } from '@viniaraujo68/plinth/components';
	import { t } from '$lib/i18n.svelte.js';
	import { unitLabel, unitOptions } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import EvolutionChart from './EvolutionChart.svelte';

	/**
	 * @type {{
	 *   evolution: import('$lib/types.js').Evolution,
	 *   minMatchdays: number,
	 *   unit: import('$lib/metrics.js').Unit,
	 *   onUnit: (unit: import('$lib/metrics.js').Unit) => void
	 * }}
	 */
	let { evolution, minMatchdays, unit: requestedUnit, onUnit } = $props();

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

	const dayView = getDayTypeView();
	const unit = $derived(visibleUnit(requestedUnit, dayView.single));
	const unitChoices = $derived(unitOptions(dayView.single ? SINGLE_GAME_UNITS : undefined));

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
			<h3 class="font-semibold">{title}</h3>
			<div class="controls">
				<SegmentedControl
					options={metrics}
					value={metric}
					label={t('chart.metric')}
					onchange={(id) => (metric = /** @type {any} */ (id))}
				/>
				{#if metric !== 'win_rate'}
					<SegmentedControl
						options={unitChoices}
						value={unit}
						label={t('unit.label')}
						onchange={(id) => onUnit(/** @type {import('$lib/metrics.js').Unit} */ (id))}
					/>
				{/if}
			</div>
		</div>
		<EvolutionChart {evolution} {metric} {unit} {minMatchdays} />
	</div>
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
