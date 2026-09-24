<script>
	import { SegmentedControl } from '@viniaraujo68/plinth/components';
	import { onMount } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { readChartTheme } from '$lib/chartTheme.js';
	import { formatNumber, formatRate, formatShortDate } from '$lib/format.svelte.js';
	import { i18n, t } from '$lib/i18n.svelte.js';
	import { unitLabel } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';

	const tracking = getTracking();

	/**
	 * @type {{
	 *   playerId: number,
	 *   playerName: string,
	 *   evolution: import('$lib/types.js').Evolution,
	 *   history: import('$lib/types.js').PlayerMatchdayRow[]
	 * }}
	 */
	let { playerId, playerName, evolution, history } = $props();

	const theme = getThemeContext();

	let rateCanvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	let goalsCanvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let rateChart = null;
	/** @type {import('chart.js').Chart | null} */
	let goalsChart = null;
	let renderTicket = 0;
	let goalsUnit = $state(/** @type {'total'|'match'} */ ('total'));

	const goalsUnits = $derived([
		{ id: 'total', label: t('player.goalsInDay') },
		{ id: 'match', label: unitLabel('match') }
	]);

	const own = $derived(evolution.series.find((s) => s.player_id === playerId) ?? null);

	const average = $derived.by(() => {
		return evolution.dates.map((_, index) => {
			const values = evolution.series
				.map((s) => s.points[index]?.win_rate)
				.filter((v) => v !== null && v !== undefined);
			if (values.length === 0) return null;
			return values.reduce((a, b) => a + b, 0) / values.length;
		});
	});

	const goalsSeries = $derived([...history].reverse());
	const hasGoals = $derived(
		tracking.trackScorers && goalsSeries.some((row) => row.goals > 0)
	);

	async function render() {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return;

		const host = rateCanvas?.parentElement ?? goalsCanvas?.parentElement ?? document.body;
		const theme = readChartTheme(host);
		const axisColor = theme.axis;
		const gridColor = theme.grid;
		const surface = theme.surface;
		const primary = theme.read('var(--series-1)', '#2a78d6');
		const neutral = theme.ink(38, 'rgba(127,127,127,0.4)');
		const accent = theme.read('var(--series-3)', '#1baf7a');

		const tooltipBase = {
			...theme.tooltip,
			boxPadding: 4,
			usePointStyle: true
		};

		if (rateChart) rateChart.destroy();
		if (rateCanvas && own) {
			const labels = evolution.dates.map(formatShortDate);
			const pointRadius = evolution.dates.length <= 24 ? 4 : 0;
			rateChart = new Chart(rateCanvas, {
				type: 'line',
				data: {
					labels,
					datasets: [
						{
							label: playerName,
							data: own.points.map((p) => (p.win_rate === null ? null : p.win_rate * 100)),
							borderColor: primary,
							backgroundColor: primary,
							tension: 0.3,
							borderWidth: 2,
							pointRadius,
							pointBorderColor: surface,
							pointBorderWidth: pointRadius > 0 ? 2 : 0,
							pointHoverRadius: 5
						},
						{
							label: t('player.groupAverage'),
							data: average.map((v) => (v === null ? null : v * 100)),
							borderColor: neutral,
							backgroundColor: neutral,
							borderDash: [6, 4],
							tension: 0.3,
							borderWidth: 2,
							pointRadius: 0,
							pointHoverRadius: 4
						}
					]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					interaction: { mode: 'index', intersect: false },
					plugins: {
						legend: { display: false },
						tooltip: {
							...tooltipBase,
							filter: (item) => item.parsed.y !== null,
							callbacks: {
								labelPointStyle: () => ({ pointStyle: 'line', rotation: 0 }),
								labelColor: (ctx) => {
									const color = String(ctx.dataset.borderColor);
									return { borderColor: color, backgroundColor: color, borderWidth: 2 };
								},
								label: (ctx) => `${ctx.dataset.label}: ${formatRate((ctx.parsed.y ?? 0) / 100)}`
							}
						}
					},
					scales: {
						x: { grid: { color: gridColor }, ticks: { color: axisColor } },
						y: {
							min: 0,
							max: 100,
							grid: { color: gridColor },
							ticks: { color: axisColor, callback: (v) => formatRate(Number(v) / 100) }
						}
					}
				}
			});
		}

		if (goalsChart) goalsChart.destroy();
		if (goalsCanvas && hasGoals) {
			goalsChart = new Chart(goalsCanvas, {
				type: 'bar',
				data: {
					labels: goalsSeries.map((row) => formatShortDate(row.date)),
					datasets: [
						{
							label: t('player.goalsChart'),
							data: goalsSeries.map((row) =>
								goalsUnit === 'match' ? (row.played ? row.goals / row.played : 0) : row.goals
							),
							backgroundColor: accent,
							borderRadius: 4,
							borderSkipped: 'bottom',
							borderWidth: 2,
							borderColor: surface,
							maxBarThickness: 34
						}
					]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { display: false },
						tooltip: {
							...tooltipBase,
							callbacks: {
								label: (ctx) => {
									const row = goalsSeries[ctx.dataIndex];
									const goals = t('records.goals', { count: row.goals });
									const matches = t('analysis.matches', { count: row.played });
									return goalsUnit === 'match'
										? `${formatNumber(ctx.parsed.y)} · ${goals} · ${matches}`
										: `${goals} · ${matches}`;
								}
							}
						}
					},
					scales: {
						x: { grid: { display: false }, ticks: { color: axisColor } },
						y: {
							beginAtZero: true,
							grid: { color: gridColor },
							ticks:
								goalsUnit === 'match'
									? { color: axisColor }
									: { color: axisColor, precision: 0, stepSize: 1 }
						}
					}
				}
			});
		}

		theme.dispose();
	}

	onMount(() => () => {
		rateChart?.destroy();
		goalsChart?.destroy();
	});

	$effect(() => {
		evolution;
		history;
		goalsUnit;
		i18n.locale;
		theme.preference;
		theme.dark;
		if (!rateCanvas && !goalsCanvas) return;
		render();
	});
</script>

<div class="charts">
	{#if own}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div>
				<h3 class="font-semibold">{t('stats.evolution')}</h3>
				<p class="hint">{t('stats.evolutionHint')}</p>
			</div>
			<div class="chart-wrap"><canvas bind:this={rateCanvas}></canvas></div>
			<div class="legend">
				<span class="key"><i class="dash solid"></i>{playerName}</span>
				<span class="key"><i class="dash dotted"></i>{t('player.groupAverage')}</span>
			</div>
		</section>
	{/if}

	{#if hasGoals}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div class="goalshead">
				<h3 class="font-semibold">
					{goalsUnit === 'match' ? t('player.goalsPerMatchChart') : t('player.goalsChart')}
				</h3>
				<SegmentedControl
					options={goalsUnits}
					value={goalsUnit}
					label={t('unit.label')}
					onchange={(id) => (goalsUnit = /** @type {'total'|'match'} */ (id))}
				/>
			</div>
			<div class="chart-wrap short"><canvas bind:this={goalsCanvas}></canvas></div>
		</section>
	{/if}
</div>

<style>
	.charts {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.chart-wrap {
		position: relative;
		height: 280px;
		width: 100%;
	}
	.goalshead {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	.chart-wrap.short {
		height: 190px;
	}
	.hint {
		margin-top: 3px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
		font-size: 0.78rem;
		color: var(--ink-muted);
	}
	.key {
		display: inline-flex;
		align-items: center;
		gap: 7px;
	}
	.dash {
		width: 20px;
		height: 0;
		border-top-width: 2px;
	}
	.dash.solid {
		border-top-style: solid;
		border-top-color: var(--series-1);
	}
	.dash.dotted {
		border-top-style: dashed;
		border-top-color: color-mix(in oklch, var(--color-base-content) 38%, transparent);
	}
</style>
