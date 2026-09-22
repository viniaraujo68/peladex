<script>
	import { onMount } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { formatNumber, formatRate } from '$lib/format.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';

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

		const host = goalsCanvas?.parentElement ?? document.body;
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

		resolve.done();
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
				<div class="scopes" role="group" aria-label={t('chart.metric')}>
					{#each scopes as option (option.id)}
						<button
							type="button"
							class="schip"
							class:sel={scope === option.id}
							aria-pressed={scope === option.id}
							onclick={() => (scope = /** @type {any} */ (option.id))}
						>
							{option.label}
						</button>
					{/each}
				</div>
			</div>
			<div class="wrap"><canvas bind:this={goalsCanvas}></canvas></div>
		</section>
	{/if}
</div>

<style>
	.timeline {
		--series-1: light-dark(#2a78d6, #3987e5);
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
	.scopes {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.schip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.schip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
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
