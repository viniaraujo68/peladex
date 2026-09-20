<script>
	import { formatRate, formatRateDelta, formatShortDate, rateClass } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import PeriodFilter from './PeriodFilter.svelte';

	/**
	 * @type {{
	 *   players: { id: number, name: string }[],
	 *   run: (body: {
	 *     together: number[], against: number[],
	 *     date_from: string|null, date_to: string|null
	 *   }) => Promise<import('$lib/types.js').ComboResult>
	 * }}
	 */
	let { players, run } = $props();

	let together = $state(/** @type {number[]} */ ([]));
	let against = $state(/** @type {number[]} */ ([]));
	let period = $state({ from: '', to: '' });
	let result = $state(/** @type {import('$lib/types.js').ComboResult|null} */ (null));
	let busy = $state(false);
	let error = $state('');

	const sorted = $derived(
		[...players].sort((a, b) => a.name.localeCompare(b.name, localeTag()))
	);

	/** @param {number[]} list @param {number} id */
	function toggle(list, id) {
		return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
	}

	/** @param {number} id */
	function pickTogether(id) {
		together = toggle(together, id);
		against = against.filter((x) => x !== id);
	}

	/** @param {number} id */
	function pickAgainst(id) {
		against = toggle(against, id);
		together = together.filter((x) => x !== id);
	}

	function clear() {
		together = [];
		against = [];
		result = null;
		error = '';
	}

	$effect(() => {
		const body = {
			together: [...together],
			against: [...against],
			date_from: period.from || null,
			date_to: period.to || null
		};
		if (body.together.length === 0) {
			result = null;
			error = '';
			return;
		}
		let cancelled = false;
		busy = true;
		const timer = setTimeout(() => {
			run(body)
				.then((data) => {
					if (cancelled) return;
					result = data;
					error = '';
				})
				.catch((e) => {
					if (!cancelled) error = e?.message ?? String(e);
				})
				.finally(() => {
					if (!cancelled) busy = false;
				});
		}, 320);
		return () => {
			cancelled = true;
			clearTimeout(timer);
		};
	});
</script>

<div class="combo">
	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<p class="text-sm text-base-content/80">{t('analysis.subtitle')}</p>
		<PeriodFilter from={period.from} to={period.to} onchange={(range) => (period = range)} />
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="pickhead">
			<h3 class="ptitle">{t('analysis.together')}</h3>
			{#if together.length || against.length}
				<button type="button" class="btn btn-ghost btn-xs" onclick={clear}>
					{t('analysis.clear')}
				</button>
			{/if}
		</div>
		<div class="picker">
			{#each sorted as player (player.id)}
				<button
					type="button"
					class="pk"
					class:sel={together.includes(player.id)}
					aria-pressed={together.includes(player.id)}
					onclick={() => pickTogether(player.id)}
				>
					{player.name}
				</button>
			{/each}
		</div>

		<div class="pickhead">
			<h3 class="ptitle">
				{t('analysis.against')}
				<span class="opt">{t('analysis.againstOptional')}</span>
			</h3>
		</div>
		<div class="picker">
			{#each sorted as player (player.id)}
				<button
					type="button"
					class="pk foe"
					class:sel={against.includes(player.id)}
					aria-pressed={against.includes(player.id)}
					disabled={together.includes(player.id)}
					onclick={() => pickAgainst(player.id)}
				>
					{player.name}
				</button>
			{/each}
		</div>
		<p class="hint">{t('analysis.pickPlayers')}</p>
	</section>

	{#if error}
		<div class="alert alert-soft alert-error">{error}</div>
	{:else if together.length === 0}
		<div class="card bg-base-100 px-5 py-10 text-center text-base-content/65">
			{t('analysis.noSelection')}
		</div>
	{:else if busy && !result}
		<div class="card bg-base-100 px-5 py-10 text-center text-base-content/65">
			{t('analysis.running')}
		</div>
	{:else if result}
		{#if result.days === 0}
			<div class="card bg-base-100 px-5 py-10 text-center text-base-content/65">
				{t('analysis.noDays')}
			</div>
		{:else}
			<section class="card flex flex-col gap-4 bg-base-100 p-5" class:busy>
				<div class="tiles">
					<div class="tile">
						<span class="tl">{t('ranking.winRate')}</span>
						<span class="tv primary">{formatRate(result.win_rate)}</span>
						<span class="ts">
							{t('analysis.days', { count: result.days })} ·
							{t('analysis.matches', { count: result.matches })}
						</span>
					</div>
					<div class="tile">
						<span class="tl">{t('analysis.record')}</span>
						<span class="tv">{result.wins}·{result.draws}·{result.losses}</span>
						<span class="ts">{result.points} pts</span>
					</div>
					<div class="tile">
						<span class="tl">{t('analysis.goalsLabel')}</span>
						<span class="tv">{result.goals_for}<span class="sep">:</span>{result.goals_against}</span>
					</div>
					<div class="tile">
						<span class="tl">{t('analysis.deltaLabel')}</span>
						<span class="tv {rateClass(result.delta)}">{formatRateDelta(result.delta)}</span>
						<span class="ts">
							{t('analysis.baseline')}: {formatRate(result.baseline)}
						</span>
					</div>
				</div>

				<div class="dates">
					<span class="dl">{t('analysis.datesLabel')}</span>
					<span class="dv">
						{result.dates.map((d) => formatShortDate(d)).join(' · ')}
					</span>
				</div>
			</section>
		{/if}
	{/if}
</div>

<style>
	.combo {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.pickhead {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.ptitle {
		font-size: 0.74rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.opt {
		font-weight: 400;
		text-transform: none;
		letter-spacing: 0;
	}
	.picker {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.pk {
		min-height: 36px;
		padding: 5px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--color-base-content);
		font-size: 0.82rem;
		cursor: pointer;
	}
	.pk:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}
	.pk.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 16%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.pk.foe.sel {
		border-color: var(--color-warning);
		background: color-mix(in oklch, var(--color-warning) 18%, transparent);
		color: var(--ink-warning);
	}
	.hint {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.busy {
		opacity: 0.6;
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 12px;
	}
	.tile {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.tl {
		font-size: 0.64rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.tv {
		font-size: 1.5rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
	.tv.primary {
		color: var(--ink-primary);
	}
	.sep {
		margin: 0 2px;
		opacity: 0.4;
	}
	.ts {
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
	.dates {
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding-top: 12px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
	}
	.dl {
		font-size: 0.64rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.dv {
		font-size: 0.78rem;
		color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
		line-height: 1.6;
	}
	@media (max-width: 560px) {
		.pk {
			min-height: 40px;
		}
	}
</style>
