<script>
	import { onMount, untrack } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { formatAverage, formatRate } from '$lib/format.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   evolution: import('$lib/types.js').Evolution,
	 *   metric?: 'win_rate'|'goals'|'assists',
	 *   unit?: import('$lib/metrics.js').Unit,
	 *   minMatchdays?: number
	 * }}
	 */
	let { evolution, metric = 'win_rate', unit = 'total', minMatchdays = 0 } = $props();

	const isRate = $derived(metric === 'win_rate');
	const isAverage = $derived(!isRate && unit !== 'total');

	/** @param {number|null|undefined} value */
	function formatValue(value) {
		if (value === null || value === undefined) return '—';
		if (isRate) return formatRate(value / 100);
		return isAverage ? formatAverage(value) : String(value);
	}

	const theme = getThemeContext();

	/**
	 * @typedef {object} Series
	 * @property {string} id
	 * @property {string} label
	 * @property {string} color
	 * @property {number[]} dash
	 * @property {string} fill
	 * @property {(number|null)[]} values
	 * @property {number} matchdays
	 */

	const HUE_COUNT = 8;
	const DASH_PATTERNS = [[], [7, 5], [10, 4, 2, 4]];
	const SWATCH_DASH_SCALE = 0.62;
	const DIRECT_LABEL_MAX_SERIES = 4;
	const DIRECT_LABEL_MIN_CANVAS = 520;
	const DIRECT_LABEL_MAX_WIDTH = 120;
	const DIRECT_LABEL_GAP = 15;
	const MAX_DEFAULT_SERIES = 5;

	let canvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let chart = null;
	let renderTicket = 0;

	let hiddenOverride = $state(/** @type {string[]|null} */ (null));

	const series = $derived(buildSeries(evolution, metric, unit));
	const defaultHidden = $derived.by(() => {
		if (series.length <= MAX_DEFAULT_SERIES) return [];
		const ranked = [...series].sort((a, b) => (currentValue(b) ?? 0) - (currentValue(a) ?? 0));
		const eligible = ranked.filter(
			(s) => (!isRate && !isAverage) || s.matchdays >= minMatchdays
		);
		const keep = new Set(eligible.slice(0, MAX_DEFAULT_SERIES).map((s) => s.id));
		return series.filter((s) => !keep.has(s.id)).map((s) => s.id);
	});
	const hiddenIds = $derived(hiddenOverride ?? defaultHidden);
	const hiddenCount = $derived(series.filter((s) => hiddenIds.includes(s.id)).length);
	const allHidden = $derived(series.length > 0 && hiddenCount === series.length);

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

	/**
	 * @param {import('$lib/types.js').EvolutionSeries} s
	 * @param {number} length
	 * @param {'win_rate'|'goals'|'assists'} kind
	 * @param {import('$lib/metrics.js').Unit} per
	 * @returns {(number|null)[]}
	 */
	function valuesOf(s, length, kind, per) {
		return Array.from({ length }, (_, i) => {
			const point = s.points[i];
			if (!point) return null;
			if (kind === 'win_rate') {
				return point.win_rate === null || point.win_rate === undefined
					? null
					: point.win_rate * 100;
			}
			const count = kind === 'goals' ? point.goals : point.assists;
			if (count === null || count === undefined) return null;
			if (per === 'total') return count;
			const divisor = per === 'match' ? point.matches : point.matchdays;
			return divisor ? count / divisor : null;
		});
	}

	/** @param {number[]} dash */
	function swatchFill(dash) {
		if (dash.length === 0) return 'var(--swatch)';
		let offset = 0;
		const stops = dash.map((run, i) => {
			const start = offset;
			offset += run * SWATCH_DASH_SCALE;
			const paint = i % 2 === 0 ? 'var(--swatch)' : 'transparent';
			return `${paint} ${start.toFixed(2)}px ${offset.toFixed(2)}px`;
		});
		return `repeating-linear-gradient(90deg, ${stops.join(', ')})`;
	}

	/**
	 * @param {import('$lib/types.js').Evolution|undefined} data
	 * @param {'win_rate'|'goals'|'assists'} kind
	 * @param {import('$lib/metrics.js').Unit} per
	 * @returns {Series[]}
	 */
	function buildSeries(data, kind, per) {
		const incoming = data?.series ?? [];
		const length = data?.dates?.length ?? 0;
		/** @type {Map<number, number>} */
		const slots = new Map();
		[...incoming]
			.sort((a, b) => a.player_id - b.player_id)
			.forEach((s, i) => slots.set(s.player_id, i));

		return incoming.map((s) => {
			const slot = slots.get(s.player_id) ?? 0;
			const dash = DASH_PATTERNS[Math.min(Math.floor(slot / HUE_COUNT), DASH_PATTERNS.length - 1)];
			return {
				id: String(s.player_id),
				label: s.name,
				color: `var(--series-${(slot % HUE_COUNT) + 1})`,
				dash,
				fill: swatchFill(dash),
				values: valuesOf(s, length, kind, per),
				matchdays: s.points.at(-1)?.matchdays ?? 0
			};
		});
	}

	/** @param {Series} s */
	function currentValue(s) {
		for (let i = s.values.length - 1; i >= 0; i--) {
			if (s.values[i] !== null) return s.values[i];
		}
		return null;
	}

	/** @param {string} id */
	function isHidden(id) {
		return hiddenIds.includes(id);
	}

	/** @param {string} id */
	function toggle(id) {
		hiddenOverride = isHidden(id)
			? hiddenIds.filter((h) => h !== id)
			: [...hiddenIds, id];
		syncVisibility();
	}

	function showAll() {
		hiddenOverride = [];
		syncVisibility();
	}

	function hideAll() {
		hiddenOverride = series.map((s) => s.id);
		syncVisibility();
	}

	function syncVisibility() {
		if (!chart) return;
		series.forEach((s, i) => chart?.setDatasetVisibility(i, !isHidden(s.id)));
		chart.update();
	}

	/** @param {string} d */
	function labelFor(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString(localeTag(), {
			day: '2-digit',
			month: 'short'
		});
	}

	/**
	 * @param {string[]} dates
	 * @param {Series[]} entries
	 */
	async function render(dates, entries) {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return;
		if (chart) chart.destroy();
		if (!canvas) return;

		const host = canvas.parentElement ?? document.body;
		const resolve = colorResolver(host);
		const ink = (/** @type {number} */ percent, /** @type {string} */ fallback) =>
			resolve.read(
				`color-mix(in oklch, var(--color-base-content) ${percent}%, transparent)`,
				fallback
			);
		const textColor = ink(85, '#c8cee0');
		const axisColor = ink(65, '#857da3');
		const gridColor = ink(10, 'rgba(127,127,127,0.12)');
		const crosshairColor = ink(28, 'rgba(127,127,127,0.3)');
		const surface = resolve.read('var(--color-base-100)', '#ffffff');
		const fontFamily = getComputedStyle(host).fontFamily;
		const labelFont = `500 11px ${fontFamily}`;

		const hiddenNow = untrack(() => new Set(hiddenIds));
		const labels = dates.map(labelFor);
		const pointRadius = dates.length <= 24 ? 4 : 0;

		const datasets = entries.map((s) => {
			const color = resolve.read(s.color, '#2a78d6');
			return {
				label: s.label,
				data: [...s.values],
				borderColor: color,
				backgroundColor: color,
				hidden: hiddenNow.has(s.id),
				tension: 0.3,
				borderWidth: 2,
				borderDash: s.dash,
				pointRadius,
				pointBorderColor: surface,
				pointBorderWidth: pointRadius > 0 ? 2 : 0,
				pointHoverRadius: 5,
				pointHoverBorderColor: surface,
				pointHoverBorderWidth: 2
			};
		});

		const padding = { top: 8, right: 8, bottom: 0, left: 0 };

		/** @param {import('chart.js').Chart} c */
		function visibleIndexes(c) {
			return c.data.datasets.map((_, i) => i).filter((i) => c.isDatasetVisible(i));
		}

		/** @param {import('chart.js').Chart} c */
		function directLabelsFit(c) {
			const shown = visibleIndexes(c);
			return (
				shown.length >= 1 &&
				shown.length <= DIRECT_LABEL_MAX_SERIES &&
				c.width >= DIRECT_LABEL_MIN_CANVAS
			);
		}

		const crosshair = {
			id: 'crosshair',
			/** @param {import('chart.js').Chart} c */
			beforeDatasetsDraw(c) {
				const active = c.getActiveElements();
				if (active.length === 0) return;
				const { x } = active[0].element;
				const ctx = c.ctx;
				ctx.save();
				ctx.beginPath();
				ctx.lineWidth = 1;
				ctx.strokeStyle = crosshairColor;
				ctx.moveTo(x, c.chartArea.top);
				ctx.lineTo(x, c.chartArea.bottom);
				ctx.stroke();
				ctx.restore();
			}
		};

		const directLabels = {
			id: 'directLabels',
			/** @param {import('chart.js').Chart} c */
			beforeLayout(c) {
				if (!directLabelsFit(c)) {
					padding.right = 8;
					return;
				}
				c.ctx.save();
				c.ctx.font = labelFont;
				const widest = visibleIndexes(c).reduce(
					(max, i) => Math.max(max, c.ctx.measureText(String(c.data.datasets[i].label)).width),
					0
				);
				c.ctx.restore();
				padding.right = 10 + Math.min(Math.ceil(widest), DIRECT_LABEL_MAX_WIDTH);
			},
			/** @param {import('chart.js').Chart} c */
			afterDatasetsDraw(c) {
				if (!directLabelsFit(c)) return;
				/** @type {{ x: number, y: number, text: string }[]} */
				const placed = [];
				for (const i of visibleIndexes(c)) {
					const values = c.data.datasets[i].data;
					let last = -1;
					for (let k = values.length - 1; k >= 0; k--) {
						if (values[k] !== null && values[k] !== undefined) {
							last = k;
							break;
						}
					}
					if (last < 0) continue;
					const element = c.getDatasetMeta(i).data[last];
					if (!element) continue;
					placed.push({ x: element.x, y: element.y, text: String(c.data.datasets[i].label) });
				}
				placed.sort((a, b) => a.y - b.y);
				let floor = c.chartArea.top + 6;
				for (const p of placed) {
					p.y = Math.min(Math.max(p.y, floor), c.chartArea.bottom);
					floor = p.y + DIRECT_LABEL_GAP;
				}
				const ctx = c.ctx;
				ctx.save();
				ctx.font = labelFont;
				ctx.fillStyle = textColor;
				ctx.textAlign = 'left';
				ctx.textBaseline = 'middle';
				for (const p of placed) ctx.fillText(p.text, p.x + 8, p.y, DIRECT_LABEL_MAX_WIDTH);
				ctx.restore();
			}
		};

		chart = new Chart(canvas, {
			type: 'line',
			data: { labels, datasets },
			plugins: [crosshair, directLabels],
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding },
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: surface,
						borderColor: ink(14, 'rgba(127,127,127,0.16)'),
						borderWidth: 1,
						titleColor: axisColor,
						bodyColor: textColor,
						padding: 10,
						cornerRadius: 8,
						boxPadding: 4,
						usePointStyle: true,
						filter: (item) => item.parsed.y !== null,
						itemSort: (a, b) => (b.parsed.y ?? 0) - (a.parsed.y ?? 0),
						callbacks: {
							labelPointStyle: () => ({ pointStyle: 'line', rotation: 0 }),
							labelColor: (ctx) => {
								const color = String(ctx.dataset.borderColor);
								return { borderColor: color, backgroundColor: color, borderWidth: 2 };
							},
							label: (ctx) => `${ctx.dataset.label}: ${formatValue(ctx.parsed.y)}`
						}
					}
				},
				scales: {
					x: { grid: { color: gridColor }, ticks: { color: axisColor } },
					y: isRate
						? {
								min: 0,
								max: 100,
								grid: { color: gridColor },
								ticks: { color: axisColor, callback: (v) => formatRate(Number(v) / 100) }
							}
						: {
								beginAtZero: true,
								grid: { color: gridColor },
								ticks: isAverage ? { color: axisColor } : { color: axisColor, precision: 0 }
							}
				}
			}
		});

		resolve.done();
	}

	onMount(() => () => chart?.destroy());

	$effect(() => {
		const dates = evolution?.dates;
		const entries = series;
		metric;
		unit;
		i18n.locale;
		theme.preference;
		theme.dark;
		if (!canvas || !dates || !entries) return;
		render(dates, entries);
	});
</script>

{#if evolution.dates.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('chart.empty')}</div>
{:else}
	<div class="evolution">
		<div class="chart-wrap">
			<canvas bind:this={canvas}></canvas>
			{#if allHidden}
				<p class="empty-overlay">{t('chart.allHidden')}</p>
			{/if}
		</div>

		{#if series.length >= 2}
			<div class="legend" role="group" aria-label={t('chart.series')}>
				{#each series as s (s.id)}
					<button
						type="button"
						class="chip"
						class:off={isHidden(s.id)}
						aria-pressed={!isHidden(s.id)}
						onclick={() => toggle(s.id)}
					>
						<span class="swatch" style="--swatch: {s.color}; --fill: {s.fill}"></span>
						<span class="name">{s.label}</span>
						<span class="value">{formatValue(currentValue(s))}</span>
					</button>
				{/each}
				<div class="legend-actions">
					{#if hiddenCount > 0}
						<button type="button" class="reset" onclick={showAll}>
							{t('chart.showAll')}
						</button>
					{/if}
					{#if hiddenCount < series.length}
						<button type="button" class="reset" onclick={hideAll}>
							{t('chart.showNone')}
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.evolution {
		--series-1: light-dark(#2a78d6, #3987e5);
		--series-2: light-dark(#eb6834, #d95926);
		--series-3: light-dark(#1baf7a, #199e70);
		--series-4: light-dark(#eda100, #c98500);
		--series-5: light-dark(#e87ba4, #d55181);
		--series-6: light-dark(#008300, #008300);
		--series-7: light-dark(#4a3aa7, #9085e9);
		--series-8: light-dark(#e34948, #e66767);
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.chart-wrap {
		position: relative;
		height: 320px;
		width: 100%;
	}
	.empty-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		font-size: 0.85rem;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		pointer-events: none;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		min-height: 36px;
		padding: 6px 12px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 14%, transparent);
		border-radius: var(--radius-field, 0.5rem);
		background-color: var(--color-base-100);
		font-size: 0.8rem;
		line-height: 1.2;
		cursor: pointer;
		transition:
			background-color 0.15s,
			border-color 0.15s,
			opacity 0.15s;
	}
	.chip:hover {
		background-color: color-mix(in oklch, var(--color-base-content) 6%, var(--color-base-100));
	}
	.chip:focus-visible,
	.reset:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	.swatch {
		flex: none;
		width: 18px;
		height: 7px;
		border-radius: 2px;
		background: var(--fill);
	}
	.name {
		font-weight: 500;
		color: var(--color-base-content);
	}
	.value {
		color: color-mix(in oklch, var(--color-base-content) 62%, transparent);
		font-variant-numeric: tabular-nums;
	}
	.chip.off {
		border-style: dashed;
		background-color: transparent;
	}
	.chip.off .swatch {
		background: none;
		box-shadow: inset 0 0 0 1.5px var(--swatch);
	}
	.chip.off .name {
		color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
		text-decoration: line-through;
	}
	.chip.off .value {
		color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
	}
	.reset {
		min-height: 36px;
		padding: 6px 12px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 16%, transparent);
		border-radius: var(--radius-field, 0.5rem);
		background-color: transparent;
		color: var(--ink-muted);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
	}
	.reset:hover {
		background-color: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		color: var(--color-base-content);
	}
	.legend-actions {
		display: flex;
		gap: 6px;
	}
	@media (max-width: 560px) {
		.chip,
		.reset {
			min-height: 44px;
		}
	}
</style>
