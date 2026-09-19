<script>
	import { formatMatchdayDate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';
	import StandingsTable from './StandingsTable.svelte';

	/**
	 * @type {{
	 *   matchday: import('$lib/types.js').Matchday,
	 *   editable?: boolean,
	 *   open?: boolean,
	 *   showMismatch?: boolean,
	 *   playerHref?: (playerId: number) => string,
	 *   onEdit?: (m: import('$lib/types.js').Matchday) => void,
	 *   onDelete?: (m: import('$lib/types.js').Matchday) => void
	 * }}
	 */
	let {
		matchday,
		editable = false,
		open = false,
		showMismatch = true,
		playerHref,
		onEdit,
		onDelete
	} = $props();

	// svelte-ignore state_referenced_locally
	let expanded = $state(open);

	const champion = $derived(
		matchday.standings.find((s) => s.team_id === matchday.champion_team_id) ?? null
	);
	const topScorer = $derived(matchday.top_scorers[0] ?? null);
	const topScorers = $derived(
		topScorer ? matchday.top_scorers.filter((s) => s.goals === topScorer.goals) : []
	);

	/** @param {import('$lib/types.js').Match} match */
	function scorersOf(match) {
		return match.goals.map((g) => ({
			...g,
			side: g.team_id === match.home_team_id ? 'home' : 'away'
		}));
	}
</script>

<article class="card bg-base-100 p-4">
	<header class="head">
		<div class="head-main">
			<h3 class="date">{formatMatchdayDate(matchday.date)}</h3>
			<div class="chips">
				{#if matchday.venue_name}
					<span class="badge badge-soft badge-sm">
						<Icon name="venue" />
						{matchday.venue_name}
					</span>
				{/if}
				<span class="badge badge-soft badge-sm">
					{t('day.matchCount', { count: matchday.matches.length })}
				</span>
				<span class="badge badge-soft badge-sm">
					{t('day.totalGoals', { count: matchday.total_goals })}
				</span>
				{#if showMismatch && matchday.goal_mismatch}
					<span class="badge badge-soft badge-warning badge-sm" title={t('day.goalMismatch')}>
						<Icon name="warning" />
						{t('day.mismatchChip')}
					</span>
				{/if}
			</div>
		</div>
		{#if editable}
			<div class="actions">
				<button
					class="btn btn-ghost btn-sm btn-square hit-44"
					aria-label={t('common.edit')}
					onclick={() => onEdit?.(matchday)}
				>
					<Icon name="edit" class="size-4" />
				</button>
				<button
					class="btn btn-ghost btn-sm btn-square hit-44"
					aria-label={t('common.delete')}
					onclick={() => onDelete?.(matchday)}
				>
					<Icon name="close" class="size-4" />
				</button>
			</div>
		{/if}
	</header>

	<div class="highlights">
		<div class="hl">
			<span class="hl-label">{t('day.champion')}</span>
			{#if champion}
				<span class="hl-value"><Icon name="trophy" class="size-4" />{champion.name}</span>
			{:else}
				<span class="hl-value muted">{t('day.noChampion')}</span>
			{/if}
		</div>
		<div class="hl">
			<span class="hl-label">{t('day.topScorer')}</span>
			{#if topScorers.length}
				<span class="hl-value">
					<Icon name="ball" class="size-4" />
					{topScorers.map((s) => s.name).join(', ')}
					<span class="muted">({topScorer?.goals})</span>
				</span>
			{:else}
				<span class="hl-value muted">—</span>
			{/if}
		</div>
		<div class="hl">
			<span class="hl-label">{t('day.mvp')}</span>
			{#if matchday.mvp_name}
				<span class="hl-value"><Icon name="star" class="size-4" />{matchday.mvp_name}</span>
			{:else}
				<span class="hl-value muted">{t('day.noMvp')}</span>
			{/if}
		</div>
	</div>

	<button
		type="button"
		class="expander"
		aria-expanded={expanded}
		onclick={() => (expanded = !expanded)}
	>
		<span>{expanded ? t('day.lineup') : t('day.matches')}</span>
		<span class="caret" class:open={expanded}><Icon name="chevron" class="size-4" /></span>
	</button>

	{#if expanded}
		<div class="body">
			<StandingsTable
				standings={matchday.standings}
				championTeamId={matchday.champion_team_id}
				{playerHref}
			/>

			<div class="matches">
				{#each matchday.matches as match (match.id)}
					{@const goals = scorersOf(match)}
					<div class="match">
						<span class="side home" class:win={match.home_score > match.away_score}>
							{match.home_team_name}
						</span>
						<span class="score">{match.home_score}<i>x</i>{match.away_score}</span>
						<span class="side away" class:win={match.away_score > match.home_score}>
							{match.away_team_name}
						</span>
						{#if goals.length}
							<span class="goals">
								{#each goals as goal (goal.id)}
									<span class="goal" class:own={goal.own_goal}>
										{goal.player_name}{#if goal.own_goal}<i> ({t('day.ownGoalShort')})</i>{/if}
									</span>
								{/each}
							</span>
						{/if}
					</div>
				{/each}
				{#if matchday.matches.length === 0}
					<p class="empty">{t('day.noMatches')}</p>
				{/if}
			</div>

			{#if matchday.notes}
				<p class="notes">{matchday.notes}</p>
			{/if}
		</div>
	{/if}
</article>

<style>
	.head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.head-main {
		display: flex;
		flex-direction: column;
		gap: 7px;
		min-width: 0;
	}
	.date {
		font-weight: 600;
		font-size: 1.02rem;
		text-transform: capitalize;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.actions {
		display: flex;
		gap: 2px;
		flex: none;
	}
	.highlights {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 10px;
		margin-top: 14px;
	}
	.hl {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.hl-label {
		font-size: 0.64rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.hl-value {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-weight: 600;
		font-size: 0.92rem;
		overflow-wrap: anywhere;
	}
	.muted {
		color: var(--ink-muted);
		font-weight: 400;
	}
	.expander {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		min-height: 40px;
		margin-top: 12px;
		padding-top: 10px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
		background: none;
		border-left: 0;
		border-right: 0;
		border-bottom: 0;
		color: var(--ink-muted);
		font: inherit;
		font-size: 0.78rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		text-transform: uppercase;
		cursor: pointer;
	}
	.expander:hover {
		color: var(--color-base-content);
	}
	.caret {
		display: inline-flex;
		transition: transform 0.15s ease;
	}
	.caret.open {
		transform: rotate(180deg);
	}
	.body {
		display: flex;
		flex-direction: column;
		gap: 16px;
		margin-top: 12px;
	}
	.matches {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.match {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: 8px;
		padding: 7px 10px;
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
		font-size: 0.86rem;
	}
	.side {
		min-width: 0;
		overflow-wrap: anywhere;
		color: var(--ink-muted);
	}
	.side.home {
		text-align: right;
	}
	.side.away {
		text-align: left;
	}
	.side.win {
		color: var(--color-base-content);
		font-weight: 700;
	}
	.score {
		font-variant-numeric: tabular-nums;
		font-weight: 700;
		white-space: nowrap;
	}
	.score i {
		margin: 0 3px;
		font-style: normal;
		opacity: 0.4;
		font-weight: 400;
	}
	.goals {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 4px 10px;
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.goal.own {
		color: var(--ink-warning);
	}
	.goal i {
		font-style: normal;
	}
	.empty {
		padding: 16px 0;
		text-align: center;
		color: var(--ink-muted);
		font-size: 0.86rem;
	}
	.notes {
		font-size: 0.82rem;
		color: var(--ink-muted);
		white-space: pre-wrap;
	}
</style>
