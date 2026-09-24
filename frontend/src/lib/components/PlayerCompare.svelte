<script>
	import { Combobox } from '@viniaraujo68/plinth/components';
	import { formatRate, formatRateDelta, rateClass } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { formatMetric, metricById, metricValue } from '$lib/metrics.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import FormDots from './FormDots.svelte';

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   a: number|null,
	 *   b: number|null,
	 *   onPick: (pick: { a: number|null, b: number|null }) => void,
	 *   loadDetail: (id: number) => Promise<import('$lib/types.js').PlayerDetail>,
	 *   runCombo: (body: {
	 *     together: number[], against: number[], date_from: null, date_to: null
	 *   }) => Promise<import('$lib/types.js').ComboResult>,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { ranking, a, b, onPick, loadDetail, runCombo, playerHref } = $props();

	/** @typedef {import('$lib/types.js').PlayerRow} Row */
	/** @typedef {import('$lib/metrics.js').MetricId} MetricId */

	const tracking = getTracking();

	const RIVALS_SHOWN = 2;

	const options = $derived(
		[...ranking]
			.sort((x, y) => x.name.localeCompare(y.name, localeTag()))
			.map((row) => ({ value: String(row.player_id), label: row.name }))
	);

	const rowA = $derived(ranking.find((r) => r.player_id === a) ?? null);
	const rowB = $derived(ranking.find((r) => r.player_id === b) ?? null);

	const rows = $derived(
		/** @type {{ id: MetricId, unit: import('$lib/metrics.js').Unit }[]} */ ([
			{ id: 'win_rate', unit: 'total' },
			...(tracking.showRatings ? [{ id: 'rating', unit: 'total' }] : []),
			{ id: 'matchdays', unit: 'total' },
			{ id: 'matches_per_matchday', unit: 'total' },
			...(tracking.trackScorers
				? [
						{ id: 'goals', unit: 'match' },
						{ id: 'goal_share', unit: 'total' },
						{ id: 'top_scorer_days', unit: 'total' }
					]
				: []),
			...(tracking.trackScorers && tracking.trackAssists
				? [
						{ id: 'assists', unit: 'match' },
						{ id: 'assist_share', unit: 'total' },
						{ id: 'top_assister_days', unit: 'total' },
						{ id: 'top_contributor_days', unit: 'total' }
					]
				: []),
			{ id: 'titles', unit: 'total' },
			{ id: 'mvp_count', unit: 'total' }
		]).map(({ id, unit }) => ({ metric: metricById(id), unit }))
	);

	/** @param {number|null} left @param {number|null} right */
	function scale(left, right) {
		const top = Math.max(left ?? 0, right ?? 0);
		return top > 0 ? top : 1;
	}

	/** @param {{ metric: import('$lib/metrics.js').Metric, unit: import('$lib/metrics.js').Unit }} line */
	function compareLine(line) {
		if (!rowA || !rowB) return null;
		const left = metricValue(rowA, line.metric, line.unit);
		const right = metricValue(rowB, line.metric, line.unit);
		const max = scale(left, right);
		const leftText = formatMetric(left, line.metric, line.unit);
		const rightText = formatMetric(right, line.metric, line.unit);
		const tied = left === null || right === null || leftText === rightText;
		return {
			label: t(`compare.metric.${line.metric.id}`),
			left: leftText,
			right: rightText,
			leftWidth: ((left ?? 0) / max) * 100,
			rightWidth: ((right ?? 0) / max) * 100,
			winner: tied ? null : (left ?? 0) > (right ?? 0) ? 'a' : 'b'
		};
	}

	let together = $state(/** @type {import('$lib/types.js').ComboResult|null} */ (null));
	let headToHead = $state(/** @type {import('$lib/types.js').ComboResult|null} */ (null));
	let details = $state(
		/** @type {Record<number, import('$lib/types.js').PlayerDetail>} */ ({})
	);
	let error = $state('');

	$effect(() => {
		const left = a;
		const right = b;
		together = null;
		headToHead = null;
		error = '';
		if (left === null || right === null || left === right) return;
		let cancelled = false;
		Promise.all([
			runCombo({ together: [left, right], against: [], date_from: null, date_to: null }),
			runCombo({ together: [left], against: [right], date_from: null, date_to: null })
		])
			.then(([with_, against]) => {
				if (cancelled) return;
				together = with_;
				headToHead = against;
			})
			.catch((e) => {
				if (!cancelled) error = e?.message ?? String(e);
			});
		return () => {
			cancelled = true;
		};
	});

	$effect(() => {
		for (const id of [a, b]) {
			if (id === null || details[id]) continue;
			loadDetail(id)
				.then((detail) => (details = { ...details, [id]: detail }))
				.catch(() => {});
		}
	});

	/** @param {number|null} id */
	function rivals(id) {
		const detail = id === null ? null : details[id];
		if (!detail) return null;
		const measured = detail.opponents.filter((o) => o.delta !== null);
		const best = [...measured].sort((x, y) => (y.delta ?? 0) - (x.delta ?? 0));
		return {
			name: detail.name,
			minDays: detail.min_days,
			preys: best.filter((o) => (o.delta ?? 0) > 0).slice(0, RIVALS_SHOWN),
			nemeses: [...best].reverse().filter((o) => (o.delta ?? 0) < 0).slice(0, RIVALS_SHOWN)
		};
	}

	/** @param {string|null} value */
	const toId = (value) => (value ? Number(value) : null);
</script>

{#snippet rivalList(/** @type {import('$lib/types.js').PairRow[]} */ list, /** @type {string} */ title)}
	<div class="rgroup">
		<span class="rtitle">{title}</span>
		{#if list.length === 0}
			<span class="hint">—</span>
		{:else}
			{#each list as rival (rival.player_id)}
				<span class="rrow">
					<a class="link-hover font-semibold" href={playerHref(rival.player_id)}>{rival.name}</a>
					<span class="rstat {rateClass(rival.delta)}">{formatRateDelta(rival.delta)}</span>
					<span class="hint">{t('analysis.days', { count: rival.days })}</span>
				</span>
			{/each}
		{/if}
	</div>
{/snippet}

<div class="compare">
	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<div>
			<h2 class="font-semibold">{t('compare.title')}</h2>
			<p class="hint">{t('compare.hint')}</p>
		</div>
		<div class="pickers">
			<div class="pick">
				<span class="plabel" id="compare-a">{t('compare.playerA')}</span>
				<Combobox
					{options}
					value={a === null ? null : String(a)}
					onchange={(value) => onPick({ a: toId(value), b })}
					placeholder={t('compare.pick')}
					emptyLabel={t('compare.noMatch')}
					clearable={a !== null}
					clearLabel={t('common.remove')}
					aria-labelledby="compare-a"
					class="w-full"
				/>
			</div>
			<button
				type="button"
				class="btn btn-sm btn-ghost swap"
				aria-label={t('compare.swap')}
				title={t('compare.swap')}
				disabled={a === null && b === null}
				onclick={() => onPick({ a: b, b: a })}
			>
				⇄
			</button>
			<div class="pick">
				<span class="plabel" id="compare-b">{t('compare.playerB')}</span>
				<Combobox
					{options}
					value={b === null ? null : String(b)}
					onchange={(value) => onPick({ a, b: toId(value) })}
					placeholder={t('compare.pick')}
					emptyLabel={t('compare.noMatch')}
					clearable={b !== null}
					clearLabel={t('common.remove')}
					aria-labelledby="compare-b"
					class="w-full"
				/>
			</div>
		</div>
	</section>

	{#if rowA && rowB && a !== b}
		<section class="card flex flex-col gap-2 bg-base-100 p-5">
			<div class="line head">
				<a class="side left name link-hover" href={playerHref(rowA.player_id)}>{rowA.name}</a>
				<span class="mid"></span>
				<a class="side right name link-hover" href={playerHref(rowB.player_id)}>{rowB.name}</a>
			</div>
			{#each rows as line (line.metric.id)}
				{@const view = compareLine(line)}
				{#if view}
					<div class="line">
						<span class="side left">
							<span class="value" class:win={view.winner === 'a'}>{view.left}</span>
							<span class="bar"><i style="width: {view.leftWidth}%" class:win={view.winner === 'a'}></i></span>
						</span>
						<span class="mid">{view.label}</span>
						<span class="side right">
							<span class="bar"><i style="width: {view.rightWidth}%" class:win={view.winner === 'b'}></i></span>
							<span class="value" class:win={view.winner === 'b'}>{view.right}</span>
						</span>
					</div>
				{/if}
			{/each}
			<div class="line">
				<span class="side left"><FormDots form={rowA.recent_form} /></span>
				<span class="mid">{t('ranking.form')}</span>
				<span class="side right"><FormDots form={rowB.recent_form} /></span>
			</div>
			{#if !rowA.qualified || !rowB.qualified}
				<p class="hint">{t('compare.fewDays')}</p>
			{/if}
		</section>

		{#if error}
			<div class="alert alert-soft alert-error">{error}</div>
		{:else}
			<div class="duo">
				<section class="card flex flex-col gap-2 bg-base-100 p-5">
					<span class="rtitle">{t('compare.together')}</span>
					{#if !together}
						<span class="hint">{t('analysis.running')}</span>
					{:else if together.days === 0}
						<span class="hint">{t('compare.neverTogether')}</span>
					{:else}
						<span class="big">{formatRate(together.win_rate)}</span>
						<span class="hint">
							{t('analysis.days', { count: together.days })} ·
							{t('compare.recordLine', {
								wins: together.wins,
								draws: together.draws,
								losses: together.losses
							})}
						</span>
						<span class="hint">
							{t('analysis.baseline')}: {formatRate(together.baseline)}
							<span class={rateClass(together.delta)}>({formatRateDelta(together.delta)})</span>
						</span>
					{/if}
				</section>
				<section class="card flex flex-col gap-2 bg-base-100 p-5">
					<span class="rtitle">{t('compare.headToHead')}</span>
					{#if !headToHead}
						<span class="hint">{t('analysis.running')}</span>
					{:else if headToHead.matches === 0}
						<span class="hint">{t('compare.neverFaced')}</span>
					{:else}
						<div class="h2h">
							<span class="h2hside">
								<b>{headToHead.wins}</b>
								<span class="hint">{rowA.name}</span>
							</span>
							<span class="h2hside">
								<b>{headToHead.draws}</b>
								<span class="hint">{t('compare.draws')}</span>
							</span>
							<span class="h2hside">
								<b>{headToHead.losses}</b>
								<span class="hint">{rowB.name}</span>
							</span>
						</div>
						<span class="hint">
							{t('analysis.matches', { count: headToHead.matches })} ·
							{t('compare.goalsLine', {
								left: headToHead.goals_for,
								right: headToHead.goals_against
							})}
						</span>
					{/if}
				</section>
			</div>
		{/if}
	{/if}

	{#if rowA || rowB}
		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div>
				<h3 class="font-semibold">{t('compare.rivals')}</h3>
				<p class="hint">{t('compare.rivalsHint')}</p>
			</div>
			<div class="duo">
				{#each [a, b] as id, index (index)}
					{@const view = rivals(id)}
					{#if id !== null && !(index === 1 && a === b)}
						<div class="rcol">
							{#if view}
								<span class="rname">{view.name}</span>
								{@render rivalList(view.preys, t('compare.prey'))}
								{@render rivalList(view.nemeses, t('compare.nemesis'))}
								{#if view.preys.length === 0 && view.nemeses.length === 0}
									<span class="hint">{t('compare.noRivals', { count: view.minDays })}</span>
								{/if}
							{:else}
								<span class="hint">{t('analysis.running')}</span>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
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
	.pickers {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: end;
		gap: 10px;
	}
	.pick {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.plabel,
	.rtitle {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.swap {
		font-size: 1.1rem;
	}
	.line {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(90px, auto) minmax(0, 1fr);
		align-items: center;
		gap: 12px;
		padding: 4px 0;
	}
	.line.head {
		padding-bottom: 8px;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 9%, transparent);
	}
	.name {
		font-weight: 700;
		font-size: 1.05rem;
	}
	.side {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.side.left {
		justify-content: flex-end;
	}
	.mid {
		font-size: 0.72rem;
		text-align: center;
		color: var(--ink-muted);
	}
	.value {
		min-width: 3.2em;
		font-variant-numeric: tabular-nums;
		font-weight: 500;
	}
	.side.left .value {
		text-align: right;
	}
	.value.win {
		font-weight: 700;
		color: var(--ink-primary);
	}
	.bar {
		display: flex;
		flex: 1;
		height: 8px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		overflow: hidden;
	}
	.side.left .bar {
		justify-content: flex-end;
	}
	.bar i {
		display: block;
		height: 100%;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 30%, transparent);
	}
	.bar i.win {
		background: var(--color-primary);
	}
	.duo {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 16px;
	}
	.big {
		font-size: 1.6rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--ink-primary);
	}
	.h2h {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
		text-align: center;
	}
	.h2hside {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.h2hside b {
		font-size: 1.5rem;
		font-variant-numeric: tabular-nums;
	}
	.rcol {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.rname {
		font-weight: 700;
	}
	.rgroup {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.rrow {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.rstat {
		font-variant-numeric: tabular-nums;
		font-weight: 600;
	}
	@media (max-width: 560px) {
		.pickers {
			grid-template-columns: 1fr;
		}
		.swap {
			justify-self: center;
		}
		.line {
			grid-template-columns: minmax(0, 1fr) 88px minmax(0, 1fr);
			gap: 6px;
		}
		.mid {
			font-size: 0.66rem;
			overflow-wrap: anywhere;
		}
		.bar {
			display: none;
		}
	}
</style>
