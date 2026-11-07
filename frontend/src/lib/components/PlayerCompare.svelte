<script>
	import { MultiSelect, SegmentedControl } from '@viniaraujo68/plinth/components';
	import { duelLines, overallLines } from '$lib/compareLines.js';
	import { getDayTypeView } from '$lib/dayType.js';
	import { DEFAULT_SORT } from '$lib/groupView.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { DEFAULT_UNIT, unitOptions } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import ComboCard from './ComboCard.svelte';
	import DuelBars from './DuelBars.svelte';
	import RankingTable from './RankingTable.svelte';
	import SideDot from './SideDot.svelte';

	/** @typedef {import('$lib/types.js').PlayerRow} PlayerRow */
	/** @typedef {{ kind: 'versus'|'together', together: number[], against: number[] }} Matchup */

	/**
	 * @type {{
	 *   ranking: PlayerRow[],
	 *   players: { id: number, name: string }[],
	 *   a: number[],
	 *   b: number[],
	 *   period: { from: string, to: string },
	 *   onPick: (sides: { a: number[], b: number[] }) => void,
	 *   runCombo: (body: import('$lib/types.js').ComboRequest) => Promise<import('$lib/types.js').ComboResult>,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { ranking, players, a, b, period, onPick, runCombo, playerHref } = $props();

	const MAX_SIDE = 4;

	const tracking = getTracking();
	const dayView = getDayTypeView();

	const names = $derived(
		new Map([
			...players.map((p) => /** @type {[number, string]} */ ([p.id, p.name])),
			...ranking.map((r) => /** @type {[number, string]} */ ([r.player_id, r.name]))
		])
	);

	/** @param {number[]} ids */
	const listNames = (ids) =>
		new Intl.ListFormat(localeTag()).format(ids.map((id) => names.get(id) ?? '?'));

	/** @param {number} id */
	const rowOf = (id) => ranking.find((r) => r.player_id === id) ?? null;

	/** @param {number[]} ids @returns {PlayerRow[]} */
	const rowsOf = (ids) => ids.flatMap((id) => rowOf(id) ?? []);

	/** @param {number} id @returns {'a'|'b'|null} */
	const sideOf = (id) => (a.includes(id) ? 'a' : b.includes(id) ? 'b' : null);

	/** @param {'a'|'b'} key */
	function optionsFor(key) {
		const mine = key === 'a' ? a : b;
		const theirs = new Set(key === 'a' ? b : a);
		const full = mine.length >= MAX_SIDE;
		return [...names]
			.filter(([id]) => !theirs.has(id))
			.sort(([, x], [, y]) => x.localeCompare(y, localeTag()))
			.map(([id, name]) => ({
				value: String(id),
				label: name,
				disabled: full && !mine.includes(id)
			}));
	}

	/** @param {'a'|'b'} key @param {string[]} values */
	function pick(key, values) {
		const ids = values.map(Number);
		onPick(key === 'a' ? { a: ids, b } : { a, b: ids });
	}

	const matchup = $derived.by(
		/** @returns {Matchup|null} */ () => {
			if (a.length && b.length) return { kind: 'versus', together: a, against: b };
			if (a.length > 1) return { kind: 'together', together: a, against: [] };
			if (b.length > 1) return { kind: 'together', together: b, against: [] };
			return null;
		}
	);

	let result = $state(/** @type {import('$lib/types.js').ComboResult|null} */ (null));
	let error = $state('');

	$effect(() => {
		const current = matchup;
		const range = { date_from: period.from || null, date_to: period.to || null };
		result = null;
		error = '';
		if (!current) return;
		let cancelled = false;
		const timer = setTimeout(() => {
			runCombo({ together: current.together, against: current.against, ...range })
				.then((data) => {
					if (!cancelled) result = data;
				})
				.catch((e) => {
					if (!cancelled) error = e?.message ?? String(e);
				});
		}, 250);
		return () => {
			cancelled = true;
			clearTimeout(timer);
		};
	});

	const focus = $derived(
		matchup && result && result.matches > 0 ? { kind: matchup.kind, result } : null
	);

	const everyone = $derived([...a, ...b]);
	const missing = $derived(everyone.filter((id) => !rowOf(id)));

	let scope = $state(/** @type {'all'|'combo'} */ ('all'));
	const inCombo = $derived(scope === 'combo' && focus !== null);
	const scopeOptions = $derived([
		{ id: 'all', label: t('compare.scopeAll') },
		{
			id: 'combo',
			label: focus?.kind === 'versus' ? t('compare.scopeVersus') : t('compare.scopeTogether')
		}
	]);

	let tableUnit = $state(DEFAULT_UNIT);
	let sort = $state(DEFAULT_SORT);
	let duelUnit = $state(/** @type {'match'|'day'} */ ('match'));
	const shownDuelUnit = $derived(dayView.single ? 'match' : duelUnit);

	const pair = $derived.by(() => {
		if (a.length !== 1 || b.length !== 1) return null;
		const left = rowOf(a[0]);
		const right = rowOf(b[0]);
		return left && right ? { left, right } : null;
	});

	const duel = $derived.by(() => {
		if (!pair) return null;
		if (!inCombo || !focus) {
			const lines = overallLines(pair.left, pair.right, shownDuelUnit, tracking);
			return { ...pair, lines };
		}
		/** @param {number} id */
		const comboRow = (id) => focus.result.players.find((row) => row.player_id === id);
		const left = comboRow(pair.left.player_id);
		const right = comboRow(pair.right.player_id);
		return left && right ? { left, right, lines: duelLines(left, right, tracking) } : null;
	});
</script>

{#snippet side(/** @type {'a'|'b'} */ key, /** @type {number[]} */ ids, /** @type {string} */ label)}
	<div class="pick">
		<span class="plabel" id="side-{key}">{label}</span>
		<MultiSelect
			options={optionsFor(key)}
			value={ids.map(String)}
			onchange={(values) => pick(key, values)}
			placeholder={t('compare.pick')}
			searchPlaceholder={t('compare.search')}
			emptyLabel={t('compare.noMatch')}
			removeLabel={(name) => t('compare.removePlayer', { name })}
			aria-labelledby="side-{key}"
		>
			{#snippet chip(option)}
				<span class="chip"><SideDot side={key} />{option.label}</span>
			{/snippet}
		</MultiSelect>
	</div>
{/snippet}

<div class="compare">
	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<div class="titlerow">
			<h2 class="font-semibold">{t('compare.title')}</h2>
			{#if everyone.length}
				<button type="button" class="btn btn-ghost btn-xs" onclick={() => onPick({ a: [], b: [] })}>
					{t('compare.clear')}
				</button>
			{/if}
		</div>
		<div class="pickers">
			{@render side('a', a, t('compare.sideA'))}
			<button
				type="button"
				class="btn btn-sm btn-ghost swap"
				aria-label={t('compare.swap')}
				title={t('compare.swap')}
				disabled={!everyone.length}
				onclick={() => onPick({ a: b, b: a })}
			>
				⇄
			</button>
			{@render side('b', b, t('compare.sideB'))}
		</div>
	</section>

	{#if error}
		<div class="alert alert-soft alert-error">{error}</div>
	{:else if matchup && result}
		<ComboCard
			{result}
			together={matchup.together}
			against={matchup.against}
			overall={matchup.kind === 'together' ? rowsOf(matchup.together) : []}
			{listNames}
			{sideOf}
		/>
	{:else if matchup}
		<div class="card bg-base-100 px-5 py-8 text-center text-base-content/65">
			{t('compare.running')}
		</div>
	{:else if everyone.length === 1}
		<div class="card bg-base-100 px-5 py-8 text-center text-base-content/65">
			{t('compare.pickMore')}
		</div>
	{/if}

	{#if everyone.length > 1}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div class="eachhead">
				<div>
					<h3 class="font-semibold">{t('compare.eachTitle')}</h3>
					{#if inCombo && focus}
						<p class="hint">
							{t('compare.eachHintVersus', {
								matches: t('common.matches', { count: focus.result.matches }),
								days: t('common.days', { count: focus.result.days })
							})}
						</p>
					{/if}
				</div>
				{#if focus}
					<SegmentedControl
						options={scopeOptions}
						value={inCombo ? 'combo' : 'all'}
						label={t('compare.scopeLabel')}
						size="sm"
						onchange={(id) => (scope = /** @type {'all'|'combo'} */ (id))}
					/>
				{/if}
			</div>
			{#if pair && duel}
				{#if !inCombo && !dayView.single}
					<SegmentedControl
						options={unitOptions(['match', 'day'])}
						value={duelUnit}
						label={t('compare.unitLabel')}
						size="sm"
						onchange={(id) => (duelUnit = /** @type {'match'|'day'} */ (id))}
					/>
				{/if}
				<DuelBars
					left={duel.left}
					right={duel.right}
					lines={duel.lines}
					showForm={!inCombo}
					{playerHref}
				/>
				{#if !inCombo && (!pair.left.qualified || !pair.right.qualified)}
					<p class="hint">{t('compare.fewDays')}</p>
				{/if}
			{:else}
				<RankingTable
					ranking={inCombo && focus ? focus.result.players : ranking}
					previousRanking={[]}
					{playerHref}
					unit={tableUnit}
					onUnit={(value) => (tableUnit = value)}
					{sort}
					onSort={(value) => (sort = value)}
					only={everyone}
					{sideOf}
					storageKey="peladex:compare-columns"
				/>
				{#if missing.length && !inCombo}
					<p class="hint">
						{t('compare.notInPeriod', { name: listNames(missing), count: missing.length })}
					</p>
				{/if}
			{/if}
		</section>
	{/if}
</div>

<style>
	.compare {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.hint {
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.titlerow,
	.eachhead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.pickers {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		grid-template-rows: auto auto;
		gap: 6px 10px;
	}
	.pick {
		display: grid;
		grid-row: span 2;
		grid-template-rows: subgrid;
		min-width: 0;
	}
	.pick:first-child {
		grid-column: 1;
	}
	.pick:last-child {
		grid-column: 3;
	}
	.plabel {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.swap {
		grid-row: 2;
		grid-column: 2;
		align-self: center;
		font-size: 1.1rem;
	}
	@media (max-width: 560px) {
		.pickers {
			grid-template-columns: 1fr;
			grid-template-rows: none;
			gap: 10px;
		}
		.pick,
		.pick:first-child,
		.pick:last-child {
			grid-column: auto;
			grid-row: auto;
			grid-template-rows: auto auto;
			gap: 6px;
		}
		.swap {
			grid-row: auto;
			grid-column: auto;
			justify-self: center;
		}
	}
</style>
