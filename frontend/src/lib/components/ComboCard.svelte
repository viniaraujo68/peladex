<script>
	import { whenSummary } from '$lib/comboDates.js';
	import { formatRate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import SideDot from './SideDot.svelte';

	/**
	 * @type {{
	 *   result: import('$lib/types.js').ComboResult,
	 *   together: number[],
	 *   against: number[],
	 *   overall: import('$lib/types.js').PlayerRow[],
	 *   listNames: (ids: number[]) => string,
	 *   sideOf: (playerId: number) => 'a'|'b'|null
	 * }}
	 */
	let { result, together, against, overall, listNames, sideOf } = $props();

	const tracking = getTracking();

	const versus = $derived(against.length > 0);
	const scorers = $derived(
		[...result.players].sort((x, y) => y.goals + y.assists - (x.goals + x.assists))
	);
	const days = $derived(t('common.days', { count: result.days }));

	const verdict = $derived.by(() => {
		if (result.wins === result.losses) return t('compare.verdictEven');
		const leader = result.wins > result.losses ? together : against;
		return t('compare.verdictAhead', { name: listNames(leader), count: leader.length });
	});
</script>

{#snippet tile(/** @type {string} */ label, /** @type {string} */ value, /** @type {string} */ note)}
	<div class="tile">
		<span class="tl">{label}</span>
		<span class="tv">{value}</span>
		<span class="tn">{note}</span>
	</div>
{/snippet}

<section class="card mcard bg-base-100 p-5">
	{#if versus}
		<h3 class="stitle">{t('compare.versusTitle', { a: listNames(together), b: listNames(against) })}</h3>
	{:else}
		<h3 class="stitle">
			{t('compare.togetherTitle', { who: listNames(together) })}
			<span class="sub">{t('compare.anyRival')}</span>
		</h3>
	{/if}

	{#if result.matches === 0}
		<span class="empty">{t(versus ? 'compare.neverFaced' : 'compare.neverTogether')}</span>
	{:else}
		{#if versus}
			<p class="verdict">{verdict}</p>
			<div class="h2h">
				<span class="h2hside" class:lead={result.wins > result.losses}>
					<b>{result.wins}</b>
					<span class="hint">{t('compare.winsOf', { name: listNames(together) })}</span>
				</span>
				<span class="h2hside">
					<b>{result.draws}</b>
					<span class="hint">{t('compare.draws')}</span>
				</span>
				<span class="h2hside" class:lead={result.losses > result.wins}>
					<b>{result.losses}</b>
					<span class="hint">{t('compare.winsOf', { name: listNames(against) })}</span>
				</span>
			</div>
		{:else}
			<div class="hero">
				<div class="tog">
					<span class="big">{formatRate(result.win_rate)}</span>
					<span class="hint">{t('compare.rateTogether')}</span>
				</div>
				<span class="pills">
					<span class="pill w">{result.wins}{t('compare.short.win')}</span>
					<span class="pill">{result.draws}{t('compare.short.draw')}</span>
					<span class="pill l">{result.losses}{t('compare.short.loss')}</span>
				</span>
			</div>
		{/if}

		<div class="tiles">
			{@render tile(
				t('compare.tile.matches'),
				String(result.matches),
				t('compare.tile.overDays', { days })
			)}
			{@render tile(
				t('compare.tile.score'),
				`${result.goals_for} x ${result.goals_against}`,
				versus
					? t('compare.tile.scoreSides', { a: listNames(together), b: listNames(against) })
					: t('compare.tile.scoreTeam')
			)}
		</div>

		{#if tracking.trackScorers}
			<div class="people">
				<span class="tl">
					{t(tracking.trackAssists ? 'compare.scorersAssistsLead' : 'compare.scorersLead')}
				</span>
				{#each scorers as player (player.player_id)}
					<div class="person">
						<SideDot side={sideOf(player.player_id)} />
						<span class="pname">{player.name}</span>
						<span class="pstat">
							<b>{player.goals}</b>
							<small>{t('compare.short.goals')}</small>
							{#if tracking.trackAssists}
								<b>{player.assists}</b>
								<small>{t('compare.short.assists')}</small>
							{/if}
						</span>
					</div>
				{/each}
			</div>
			{#if tracking.trackAssists && result.assist_links.length}
				<div class="people">
					<span class="tl">{t('compare.assistLinksLead')}</span>
					{#each result.assist_links as link (link.assist_player_id + '-' + link.scorer_player_id)}
						<div class="person">
							<SideDot side={sideOf(link.assist_player_id)} />
							<span class="pname">
								{link.assist_name}<span class="muted">&rarr;</span>{link.scorer_name}
							</span>
							<span class="pstat"><b>{link.goals}</b></span>
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		{#if !versus && overall.length}
			<div class="people">
				<span class="tl">{t('compare.overallLead')}</span>
				<div class="rateline together">
					<span class="pname">{t('compare.togetherShort')}</span>
					<span class="rbar"><i style="width: {result.win_rate * 100}%"></i></span>
					<span class="rval">{formatRate(result.win_rate)}</span>
				</div>
				{#each overall as row (row.player_id)}
					<div class="rateline">
						<span class="pname">
							<SideDot side={sideOf(row.player_id)} />
							{row.name}
						</span>
						<span class="rbar"><i style="width: {row.win_rate * 100}%"></i></span>
						<span class="rval">{formatRate(row.win_rate)}</span>
					</div>
				{/each}
			</div>
		{/if}

		<p class="when">{whenSummary(result.dates)}</p>
	{/if}
</section>

<style>
	.mcard {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.stitle,
	.tl {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.stitle {
		overflow-wrap: anywhere;
	}
	.tl {
		font-size: 0.64rem;
	}
	.sub {
		display: block;
		font-weight: 400;
		text-transform: none;
		letter-spacing: 0;
	}
	.hint,
	.muted {
		color: var(--ink-muted);
	}
	.hint {
		font-size: 0.74rem;
	}
	.empty {
		color: var(--ink-muted);
	}
	.verdict {
		font-size: 1.1rem;
		font-weight: 600;
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
	.h2hside.lead b {
		color: var(--ink-primary);
	}
	.hero {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.tog {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.big {
		font-size: 1.6rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--ink-primary);
	}
	.pills {
		display: inline-flex;
		gap: 4px;
	}
	.pill {
		padding: 2px 9px;
		border-radius: 999px;
		font-size: 0.8rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		background: color-mix(in oklch, var(--color-base-content) 9%, transparent);
	}
	.pill.w {
		background: color-mix(in oklch, var(--color-primary) 20%, transparent);
		color: var(--ink-primary);
	}
	.pill.l {
		background: color-mix(in oklch, var(--color-error) 18%, transparent);
		color: var(--color-error);
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 8px;
	}
	.tile {
		display: flex;
		flex-direction: column;
		gap: 1px;
		min-width: 0;
		padding: 10px 12px;
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-base-content) 5%, transparent);
	}
	.tv {
		font-size: 1.15rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.tn {
		font-size: 0.68rem;
		color: var(--ink-muted);
		overflow-wrap: anywhere;
	}
	.people {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.person {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.86rem;
	}
	.pname {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.pstat {
		display: inline-flex;
		align-items: baseline;
		gap: 3px;
		margin-left: auto;
		font-variant-numeric: tabular-nums;
	}
	.pstat small {
		margin-right: 6px;
		font-size: 0.68rem;
		color: var(--ink-muted);
	}
	.pstat small:last-child {
		margin-right: 0;
	}
	.rateline {
		display: grid;
		grid-template-columns: minmax(70px, 30%) minmax(0, 1fr) 3.4em;
		align-items: center;
		gap: 8px;
		font-size: 0.82rem;
	}
	.rateline.together {
		font-weight: 700;
	}
	.rbar {
		height: 8px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		overflow: hidden;
	}
	.rbar i {
		display: block;
		height: 100%;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 30%, transparent);
	}
	.rateline.together .rbar i {
		background: var(--color-primary);
	}
	.rval {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.when {
		padding-top: 10px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 9%, transparent);
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
</style>
