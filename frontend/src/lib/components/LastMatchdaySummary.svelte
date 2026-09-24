<script>
	import { formatMatchdayDate, formatNumber } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import Icon from './Icon.svelte';
	import StandingsTable from './StandingsTable.svelte';
	import TeamCrest from './TeamCrest.svelte';

	/**
	 * @type {{
	 *   matchdays: import('$lib/types.js').Matchday[],
	 *   playerHref?: (playerId: number) => string,
	 *   onOpenDay: () => void
	 * }}
	 */
	let { matchdays, playerHref, onOpenDay } = $props();

	/** @typedef {import('$lib/types.js').Matchday} Matchday */
	/** @typedef {import('$lib/types.js').Match} Match */

	const tracking = getTracking();

	const ordered = $derived(
		[...matchdays].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
	);
	const latest = $derived(ordered[0] ?? null);
	const earlier = $derived(ordered.slice(1));

	const champion = $derived(
		latest?.standings.find((s) => s.team_id === latest.champion_team_id) ?? null
	);

	/** @template {{ player_id: number }} T @param {T[]} rows @param {(row: T) => number} count */
	function leaders(rows, count) {
		const best = rows.length ? Math.max(...rows.map(count)) : 0;
		return best > 0 ? rows.filter((row) => count(row) === best) : [];
	}

	const scorers = $derived(latest ? leaders(latest.top_scorers, (s) => s.goals) : []);
	const assisters = $derived(latest ? leaders(latest.top_assisters, (s) => s.assists) : []);

	/** @param {Match} match */
	const margin = (match) => Math.abs(match.home_score - match.away_score);

	/** @param {Matchday} day */
	function bestPlayerGoals(day) {
		/** @type {Map<number, number>} */
		const counts = new Map();
		for (const match of day.matches) {
			for (const goal of match.goals) {
				if (goal.own_goal) continue;
				counts.set(goal.player_id, (counts.get(goal.player_id) ?? 0) + 1);
			}
		}
		return Math.max(0, ...counts.values());
	}

	/** @param {Matchday} day */
	function biggestMargin(day) {
		return Math.max(0, ...day.matches.map(margin));
	}

	const records = $derived.by(() => {
		if (!latest || earlier.length === 0) return [];
		/** @type {string[]} */
		const found = [];
		const previousGoals = Math.max(...earlier.map((d) => d.total_goals));
		if (latest.total_goals > previousGoals) {
			found.push(t('summary.recordDayGoals', { count: latest.total_goals }));
		}
		if (tracking.trackScorers && scorers.length) {
			const previousBest = Math.max(...earlier.map(bestPlayerGoals));
			if (scorers[0].goals > previousBest) {
				found.push(
					t('summary.recordPlayerGoals', {
						name: scorers.map((s) => s.name).join(', '),
						count: scorers[0].goals
					})
				);
			}
		}
		const previousMargin = Math.max(...earlier.map(biggestMargin));
		if (biggestMargin(latest) > previousMargin) {
			found.push(t('summary.recordMargin', { count: biggestMargin(latest) }));
		}
		return found;
	});

	const averageGoals = $derived(
		ordered.length > 1
			? ordered.reduce((sum, day) => sum + day.total_goals, 0) / ordered.length
			: null
	);
</script>

{#snippet people(/** @type {{ player_id: number, name: string }[]} */ rows)}
	{#each rows as row, index (row.player_id)}
		{#if index > 0}, {/if}
		{#if playerHref}
			<a class="link-hover" href={playerHref(row.player_id)}>{row.name}</a>
		{:else}
			{row.name}
		{/if}
	{/each}
{/snippet}

{#if latest}
	<section class="card summary bg-base-100 p-5">
		<header class="shead">
			<div>
				<span class="eyebrow">{t('summary.title')}</span>
				<h3 class="sdate">{formatMatchdayDate(latest.date)}</h3>
			</div>
			<div class="chips">
				{#if latest.venue_name}
					<span class="badge badge-soft badge-sm"><Icon name="venue" />{latest.venue_name}</span>
				{/if}
				<span class="badge badge-soft badge-sm">
					{t('day.matchCount', { count: latest.matches.length })}
				</span>
				<span class="badge badge-soft badge-sm">
					{t('day.totalGoals', { count: latest.total_goals })}
				</span>
			</div>
		</header>

		<div class="champion">
			{#if champion}
				<TeamCrest name={champion.name} color={champion.color} class="size-9" />
				<div class="cbody">
					<span class="clabel">{t('summary.champion')}</span>
					<span class="cname">{champion.name}</span>
					<span class="crecord">
						{t('summary.record', {
							wins: champion.wins,
							draws: champion.draws,
							losses: champion.losses,
							points: champion.points
						})}
					</span>
					<span class="cmembers">{@render people(champion.members)}</span>
				</div>
			{:else}
				<Icon name="trophy" class="size-6 opacity-50" />
				<span class="text-base-content/70">{t('summary.noChampion')}</span>
			{/if}
		</div>

		<div class="highlights">
			{#if tracking.trackScorers}
				<div class="hl">
					<span class="hl-label">{t('day.topScorer')}</span>
					{#if scorers.length}
						<span class="hl-value">
							<Icon name="ball" class="size-4" />
							<span>{@render people(scorers)}</span>
							<span class="muted">({scorers[0].goals})</span>
						</span>
					{:else}
						<span class="hl-value muted">—</span>
					{/if}
				</div>
			{/if}
			{#if tracking.trackScorers && tracking.trackAssists && assisters.length}
				<div class="hl">
					<span class="hl-label">{t('day.topAssister')}</span>
					<span class="hl-value">
						<Icon name="boot" class="size-4" />
						<span>{@render people(assisters)}</span>
						<span class="muted">({assisters[0].assists})</span>
					</span>
				</div>
			{/if}
			<div class="hl">
				<span class="hl-label">{t('day.mvp')}</span>
				{#if latest.mvp_player_id && latest.mvp_name}
					<span class="hl-value">
						<Icon name="star" class="size-4" />
						<span>{@render people([{ player_id: latest.mvp_player_id, name: latest.mvp_name }])}</span>
					</span>
				{:else}
					<span class="hl-value muted">{t('day.noMvp')}</span>
				{/if}
			</div>
		</div>

		{#if latest.standings.length}
			<div class="standings">
				<span class="hl-label">{t('summary.standings')}</span>
				<StandingsTable
					standings={latest.standings}
					championTeamId={latest.champion_team_id}
					compact
				/>
			</div>
		{/if}

		{#if records.length || averageGoals !== null}
			<ul class="facts">
				{#each records as record (record)}
					<li class="fact record"><Icon name="trophy" class="size-3.5" />{record}</li>
				{/each}
				{#if averageGoals !== null}
					<li class="fact">
						{t('summary.averageGoals', {
							count: latest.total_goals,
							average: formatNumber(averageGoals)
						})}
					</li>
				{/if}
			</ul>
		{/if}

		<button type="button" class="btn btn-sm self-start" onclick={onOpenDay}>
			{t('summary.openDay')}
		</button>
	</section>
{/if}

<style>
	.summary {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.shead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: 8px 12px;
	}
	.eyebrow,
	.clabel,
	.hl-label {
		font-size: 0.6875rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.sdate {
		font-size: 1.15rem;
		font-weight: 600;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.champion {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 12px;
		border-radius: var(--radius-box);
		background: color-mix(in oklch, var(--color-primary) 9%, transparent);
	}
	.cbody {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.cname {
		font-size: 1.1rem;
		font-weight: 700;
	}
	.crecord {
		font-size: 0.8rem;
		font-variant-numeric: tabular-nums;
		color: var(--ink-muted);
	}
	.cmembers {
		margin-top: 4px;
		font-size: 0.82rem;
		overflow-wrap: anywhere;
	}
	.highlights {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 12px;
	}
	.hl {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.hl-value {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 5px;
		font-weight: 600;
	}
	.muted {
		color: var(--ink-muted);
		font-weight: 400;
	}
	.standings {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.facts {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 0.8rem;
		color: var(--ink-muted);
	}
	.fact {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.fact.record {
		font-weight: 600;
		color: var(--ink-primary);
	}
</style>
