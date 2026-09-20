<script>
	import { onMount } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { formatNumber, formatRate } from '$lib/format.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';

	/** @type {{ timeline: import('$lib/types.js').Timeline }} */
	let { timeline } = $props();

	const theme = getThemeContext();
	const tracking = getTracking();

	let goalsCanvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	let averageCanvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let goalsChart = null;
	/** @type {import('chart.js').Chart | null} */
	let averageChart = null;
	let renderTicket = 0;

	const points = $derived(timeline.points);
	const hasData = $derived(points.length > 0);
	const maxShare = $derived(
		timeline.scorelines.reduce((m, row) => Math.max(m, row.share), 0) || 1
	);

	/** @param {HTMLElement} host */
	function colorResolver(host) {
		const probe = document.createElement('span');
		probe.style.position = 'absolute';
		probe.style.visibility = 'hidden';
		probe.style.pointerEvents = 'none';
		host.appendChild(probe);
		return {
			/** @param {string} expression @param {string} fallback */
			read(expression, fallback) {
				probe.style.color = '';
				probe.style.color = expression;
				return getComputedStyle(probe).color || fallback;
			},
			done() {
				probe.remove();
			}
		};
	}

	/** @param {string} d */
	function labelFor(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString(localeTag(), {
			day: '2-digit',
			month: 'short'
		});
	}

	async function render() {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return;

		const host = goalsCanvas?.parentElement ?? averageCanvas?.parentElement ?? document.body;
		const resolve = colorResolver(host);
		const ink = (/** @type {number} */ percent, /** @type {string} */ fallback) =>
			resolve.read(
				`color-mix(in oklch, var(--color-base-content) ${percent}%, transparent)`,
				fallback
			);
		const axisColor = ink(65, '#857da3');
		const textColor = ink(85, '#c8cee0');
		const gridColor = ink(10, 'rgba(127,127,127,0.12)');
		const surface = resolve.read('var(--color-base-100)', '#ffffff');
		const bar = resolve.read('var(--series-1)', '#2a78d6');
		const line = resolve.read('var(--series-2)', '#eb6834');

		const tooltip = {
			backgroundColor: surface,
			borderColor: ink(14, 'rgba(127,127,127,0.16)'),
			borderWidth: 1,
			titleColor: axisColor,
			bodyColor: textColor,
			padding: 10,
			cornerRadius: 8
		};
		const labels = points.map((p) => labelFor(p.date));

		if (goalsChart) goalsChart.destroy();
		if (goalsCanvas) {
			goalsChart = new Chart(goalsCanvas, {
				type: 'bar',
				data: {
					labels,
					datasets: [
						{
							label: t('chart.goalsPerMatchday'),
							data: points.map((p) => p.goals),
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
									return `${t('records.goals', { count: point.goals })} · ${t(
										'analysis.matches',
										{ count: point.matches }
									)}`;
								}
							}
						}
					},
					scales: {
						x: { grid: { display: false }, ticks: { color: axisColor } },
						y: {
							beginAtZero: true,
							grid: { color: gridColor },
							ticks: { color: axisColor, precision: 0 }
						}
					}
				}
			});
		}

		if (averageChart) averageChart.destroy();
		if (averageCanvas) {
			averageChart = new Chart(averageCanvas, {
				type: 'line',
				data: {
					labels,
					datasets: [
						{
							label: t('chart.goalsPerMatch'),
							data: points.map((p) => p.goals_per_match),
							borderColor: line,
							backgroundColor: line,
							tension: 0.3,
							borderWidth: 2,
							pointRadius: points.length <= 24 ? 4 : 0,
							pointBorderColor: surface,
							pointBorderWidth: points.length <= 24 ? 2 : 0,
							pointHoverRadius: 5
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
							...tooltip,
							callbacks: {
								label: (ctx) => formatNumber(ctx.parsed.y)
							}
						}
					},
					scales: {
						x: { grid: { display: false }, ticks: { color: axisColor } },
						y: {
							beginAtZero: true,
							grid: { color: gridColor },
							ticks: { color: axisColor }
						}
					}
				}
			});
		}

		resolve.done();
	}

	onMount(() => () => {
		goalsChart?.destroy();
		averageChart?.destroy();
	});

	$effect(() => {
		timeline;
		i18n.locale;
		theme.preference;
		theme.dark;
		if (!goalsCanvas && !averageCanvas) return;
		render();
	});
</script>

<div class="timeline">
	<section class="tiles">
		<div class="tile">
			<span class="tl">{t('chart.goalsPerMatch')}</span>
			<span class="tv">{formatNumber(timeline.goals_per_match)}</span>
		</div>
		<div class="tile">
			<span class="tl">{t('chart.goalsPerMatchday')}</span>
			<span class="tv">{formatNumber(timeline.goals_per_matchday)}</span>
		</div>
		{#if tracking.trackAssists}
			<div class="tile">
				<span class="tl">{t('chart.assistsPerMatchday')}</span>
				<span class="tv">{formatNumber(timeline.assists_per_matchday)}</span>
			</div>
		{/if}
	</section>

	{#if hasData}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<h3 class="font-semibold">{t('chart.goalsPerMatchday')}</h3>
			<div class="wrap"><canvas bind:this={goalsCanvas}></canvas></div>
		</section>

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div>
				<h3 class="font-semibold">{t('chart.goalsPerMatch')}</h3>
				<p class="hint">{t('chart.goalsPerMatchHint')}</p>
			</div>
			<div class="wrap"><canvas bind:this={averageCanvas}></canvas></div>
		</section>
	{/if}

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
</div>

<style>
	.timeline {
		--series-1: light-dark(#2a78d6, #3987e5);
		--series-2: light-dark(#eb6834, #d95926);
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 12px;
	}
	.tile {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 14px 16px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		border-radius: var(--radius-box);
		background: var(--color-base-100);
	}
	.tl {
		font-size: 0.66rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.tv {
		font-size: 1.55rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
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
