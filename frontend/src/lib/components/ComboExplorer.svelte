<script>
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { Combobox } from '@viniaraujo68/plinth/components';
	import { formatShortDate } from '$lib/format.svelte.js';
	import PeriodFilter from './PeriodFilter.svelte';

	/**
	 * @type {{
	 *   players: { id: number, name: string }[],
	 *   locked?: { id: number, name: string }|null,
	 *   compact?: boolean,
	 *   run: (body: {
	 *     together: number[], against: number[],
	 *     date_from: string|null, date_to: string|null
	 *   }) => Promise<import('$lib/types.js').ComboResult>
	 * }}
	 */
	let { players, run, locked = null, compact = false } = $props();

	let together = $state(/** @type {number[]} */ ([]));
	let against = $state(/** @type {number[]} */ ([]));
	let period = $state({ from: '', to: '' });
	let result = $state(/** @type {import('$lib/types.js').ComboResult|null} */ (null));
	let busy = $state(false);
	let error = $state('');

	const sorted = $derived(
		[...players]
			.filter((p) => p.id !== locked?.id)
			.sort((a, b) => a.name.localeCompare(b.name, localeTag()))
	);

	const effectiveTogether = $derived(locked ? [locked.id, ...together] : together);

	const names = $derived(new Map(players.map((p) => [p.id, p.name])));

	/** @param {number} id */
	const nameOf = (id) => names.get(id) ?? '?';

	/** @param {string[]} dates */
	const spansYears = (dates) => dates[0].slice(0, 4) !== dates[dates.length - 1].slice(0, 4);

	/** @param {string} date @param {string[]} dates */
	function dateLabel(date, dates) {
		return spansYears(dates) ? `${formatShortDate(date)} ${date.slice(0, 4)}` : formatShortDate(date);
	}

	/** @param {string[]} dates */
	function whenSummary(dates) {
		if (dates.length === 1) return t('analysis.whenOnce', { date: dateLabel(dates[0], dates) });
		return t('analysis.whenRange', {
			count: dates.length,
			first: dateLabel(dates[0], dates),
			last: dateLabel(dates[dates.length - 1], dates)
		});
	}

	/** @param {number[]} chosen */
	function optionsFor(chosen) {
		const taken = new Set([...together, ...against, ...chosen]);
		return sorted
			.filter((p) => !taken.has(p.id))
			.map((p) => ({ value: String(p.id), label: p.name }));
	}

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
			together: [...effectiveTogether],
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
	{#if !compact}
		<section class="card flex flex-col gap-4 bg-base-100 p-5">
			<p class="text-sm text-base-content/80">{t('analysis.subtitle')}</p>
			<PeriodFilter from={period.from} to={period.to} onchange={(range) => (period = range)} />
		</section>
	{/if}

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="pickhead">
			<h3 class="ptitle">{t('analysis.together')}</h3>
			{#if together.length || against.length}
				<button type="button" class="btn btn-ghost btn-xs" onclick={clear}>
					{t('analysis.clear')}
				</button>
			{/if}
		</div>
		{#if locked || together.length}
			<div class="picker">
				{#if locked}
					<span class="pk sel locked">{locked.name}</span>
				{/if}
				{#each together as id (id)}
					<button
						type="button"
						class="pk sel"
						aria-label={t('analysis.removePlayer', { name: nameOf(id) })}
						onclick={() => pickTogether(id)}
					>
						{nameOf(id)} <span aria-hidden="true">✕</span>
					</button>
				{/each}
			</div>
		{/if}
		{#key together.join()}
			<Combobox
				options={optionsFor(together)}
				value={null}
				onchange={(value) => value && pickTogether(Number(value))}
				placeholder={t('analysis.addPlayer')}
				emptyLabel={t('compare.noMatch')}
				aria-label={t('analysis.together')}
				class="w-full max-w-sm"
			/>
		{/key}

		<div class="pickhead">
			<h3 class="ptitle">
				{t('analysis.against')}
				<span class="opt">{t('analysis.againstOptional')}</span>
			</h3>
		</div>
		{#if against.length}
			<div class="picker">
				{#each against as id (id)}
					<button
						type="button"
						class="pk foe sel"
						aria-label={t('analysis.removePlayer', { name: nameOf(id) })}
						onclick={() => pickAgainst(id)}
					>
						{nameOf(id)} <span aria-hidden="true">✕</span>
					</button>
				{/each}
			</div>
		{/if}
		{#key against.join()}
			<Combobox
				options={optionsFor(against)}
				value={null}
				onchange={(value) => value && pickAgainst(Number(value))}
				placeholder={t('analysis.addPlayer')}
				emptyLabel={t('compare.noMatch')}
				aria-label={t('analysis.against')}
				class="w-full max-w-sm"
			/>
		{/key}
		<p class="hint">{t('analysis.pickHint')}</p>
	</section>

	{#if error}
		<div class="alert alert-soft alert-error">{error}</div>
	{:else if effectiveTogether.length === 0}
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
				<div class="versus">
					<span class="vlabel">{t('analysis.actual')}</span>
					<span class="vbar"><i class="actual" style="width: {result.win_rate * 100}%"></i></span>
					<span class="vvalue">{formatRate(result.win_rate)}</span>
					<span class="vlabel">{t('analysis.baseline')}</span>
					<span class="vbar"><i style="width: {result.baseline * 100}%"></i></span>
					<span class="vvalue">{formatRate(result.baseline)}</span>
				</div>
				{#if result.dates.length}
					<div class="dates">
						<span class="tl">{t('analysis.when')}</span>
						<span class="ts">{whenSummary(result.dates)}</span>
						{#if result.dates.length > 1}
							<details class="datelist">
								<summary>{t('analysis.showDates')}</summary>
								<div class="datechips">
									{#each [...result.dates].reverse() as date (date)}
										<span class="datechip">{dateLabel(date, result.dates)}</span>
									{/each}
								</div>
							</details>
						{/if}
					</div>
				{/if}
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
	.pk.locked {
		cursor: default;
		opacity: 0.85;
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
	.versus {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: 6px 10px;
	}
	.vlabel,
	.vvalue {
		font-size: 0.74rem;
		color: var(--ink-muted);
		font-variant-numeric: tabular-nums;
	}
	.vbar {
		height: 10px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		overflow: hidden;
	}
	.vbar i {
		display: block;
		height: 100%;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 30%, transparent);
	}
	.vbar i.actual {
		background: var(--color-primary);
	}
	.dates {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.datelist summary {
		width: fit-content;
		font-size: 0.74rem;
		color: var(--ink-muted);
		cursor: pointer;
	}
	.datechips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		max-height: 9rem;
		margin-top: 6px;
		overflow-y: auto;
	}
	.datechip {
		padding: 1px 7px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		font-size: 0.72rem;
		font-variant-numeric: tabular-nums;
		color: var(--ink-muted);
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
	@media (max-width: 560px) {
		.pk {
			min-height: 40px;
		}
	}
</style>
