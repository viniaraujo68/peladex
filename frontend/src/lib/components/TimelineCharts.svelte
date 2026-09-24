<script>
	import { SegmentedControl } from '@viniaraujo68/plinth/components';
	import { onMount } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { readChartTheme } from '$lib/chartTheme.js';
	import { formatNumber, formatRate, formatShortDate } from '$lib/format.svelte.js';
	import { i18n, t } from '$lib/i18n.svelte.js';

	/** @type {{ timeline: import('$lib/types.js').Timeline }} */
	let { timeline } = $props();

	const theme = getThemeContext();

	let goalsCanvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let goalsChart = null;
	let renderTicket = 0;
	let scope = $state(/** @type {'matchday'|'match'} */ ('matchday'));

	const scopes = $derived([
		{ id: 'matchday', label: t('chart.perMatchday') },
		{ id: 'match', label: t('chart.perMatch') }
	]);

	const points = $derived(timeline.points);
	const hasData = $derived(points.length > 0);
	const maxShare = $derived(
		timeline.scorelines.reduce((m, row) => Math.max(m, row.share), 0) || 1
	);

	async function render() {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return;

		const host = goalsCanvas?.parentElement ?? document.body;
		const theme = readChartTheme(host);
		const axisColor = theme.axis;
		const gridColor = theme.grid;
		const surface = theme.surface;
		const bar = theme.read('var(--series-1)', '#2a78d6');
		const tooltip = theme.tooltip;
		const labels = points.map((p) => formatShortDate(p.date));

		const perMatch = scope === 'match';

		if (goalsChart) goalsChart.destroy();
		if (goalsCanvas) {
			goalsChart = new Chart(goalsCanvas, {
				type: 'bar',
				data: {
					labels,
					datasets: [
						{
							label: perMatch ? t('chart.goalsPerMatch') : t('chart.goalsPerMatchday'),
							data: points.map((p) => (perMatch ? p.goals_per_match : p.goals)),
							backgroundColor: bar,
							borderRadius: 4,
							borderSkipped: 'bottom',
							borderWidth: 2,
							borderColor: surface,
							maxBarThickness: 30
						}
					]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { display: false },
						tooltip: {
							...tooltip,
							callbacks: {
								label: (ctx) => {
									const point = points[ctx.dataIndex];
									const matches = t('analysis.matches', { count: point.matches });
									if (perMatch) return `${formatNumber(point.goals_per_match)} · ${matches}`;
									return `${t('records.goals', { count: point.goals })} · ${matches}`;
								}
							}
						}
					},
					scales: {
						x: { grid: { display: false }, ticks: { color: axisColor } },
						y: {
							beginAtZero: true,
							grid: { color: gridColor },
							ticks: perMatch ? { color: axisColor } : { color: axisColor, precision: 0 }
						}
					}
				}
			});
		}

		theme.dispose();
	}

	onMount(() => () => {
		goalsChart?.destroy();
	});

	$effect(() => {
		timeline;
		scope;
		i18n.locale;
		theme.preference;
		theme.dark;
		if (!goalsCanvas) return;
		render();
	});
</script>

<div class="timeline">
	{#if timeline.scorelines.length}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div>
				<h3 class="font-semibold">{t('chart.scorelines')}</h3>
				<p class="hint">{t('chart.scorelinesHint')}</p>
			</div>
			<ul class="rows">
				{#each timeline.scorelines as row (row.label)}
					<li class="row">
						<span class="rlabel">{row.label}</span>
						<span class="rbar" style="--w: {(row.share / maxShare) * 100}%"></span>
						<span class="rshare">{formatRate(row.share)}</span>
						<span class="rcount">{row.count}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if hasData}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div class="charthead">
				<div>
					<h3 class="font-semibold">
						{scope === 'match' ? t('chart.goalsPerMatch') : t('chart.goalsPerMatchday')}
					</h3>
					{#if scope === 'match'}
						<p class="hint">{t('chart.goalsPerMatchHint')}</p>
					{/if}
				</div>
				<SegmentedControl
					options={scopes}
					value={scope}
					label={t('unit.label')}
					onchange={(id) => (scope = /** @type {'matchday'|'match'} */ (id))}
				/>
			</div>
			<div class="wrap"><canvas bind:this={goalsCanvas}></canvas></div>
		</section>
	{/if}
</div>

<style>
	.timeline {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.charthead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.hint {
		margin-top: 3px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.wrap {
		position: relative;
		height: 240px;
		width: 100%;
	}
	.rows {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.row {
		display: grid;
		grid-template-columns: 3.2rem 1fr 3.2rem 2.4rem;
		align-items: center;
		gap: 10px;
		font-size: 0.84rem;
	}
	.rlabel {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.rbar {
		height: 8px;
		border-radius: 4px;
		background: linear-gradient(
			to right,
			var(--color-primary) var(--w),
			color-mix(in oklch, var(--color-base-content) 8%, transparent) var(--w)
		);
	}
	.rshare,
	.rcount {
		text-align: right;
		font-variant-numeric: tabular-nums;
		color: var(--ink-muted);
	}
	.rshare {
		color: var(--color-base-content);
		font-weight: 600;
	}
</style>
