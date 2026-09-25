<script>
	import { formatRate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';
	import TeamCrest from './TeamCrest.svelte';

	/**
	 * @type {{
	 *   standings: import('$lib/types.js').Standing[],
	 *   championTeamId?: number|null,
	 *   compact?: boolean,
	 *   playerHref?: (playerId: number) => string
	 * }}
	 */
	let { standings, championTeamId = null, compact = false, playerHref } = $props();
</script>

<div class="standings">
	<div class="scroll">
		<table class="table table-sm">
			<thead>
				<tr>
					<th class="team-col">{t('standings.team')}</th>
					<th class="num">{t('standings.played')}</th>
					<th class="num">{t('standings.wins')}</th>
					<th class="num">{t('standings.draws')}</th>
					<th class="num">{t('standings.losses')}</th>
					{#if !compact}
						<th class="num">{t('standings.goalsFor')}</th>
						<th class="num">{t('standings.goalsAgainst')}</th>
					{/if}
					<th class="num">{t('standings.goalDiff')}</th>
					<th class="num">{t('standings.points')}</th>
					<th class="num rate" title={t('standings.winRateHint')}>{t('standings.winRate')}</th>
				</tr>
			</thead>
			<tbody>
				{#each standings as row (row.team_id)}
					<tr class:champion={row.team_id === championTeamId}>
						<td class="team-col">
							<span class="team-name">
								{#if row.team_id === championTeamId}
									<Icon name="trophy" class="size-4 shrink-0 text-[var(--ink-primary)]" />
								{/if}
								<TeamCrest name={row.name} color={row.color} class="size-4 shrink-0" />
								{row.name}
							</span>
						</td>
						<td class="num">{row.played}</td>
						<td class="num">{row.wins}</td>
						<td class="num">{row.draws}</td>
						<td class="num">{row.losses}</td>
						{#if !compact}
							<td class="num">{row.goals_for}</td>
							<td class="num">{row.goals_against}</td>
						{/if}
						<td class="num">{row.goal_diff > 0 ? `+${row.goal_diff}` : row.goal_diff}</td>
						<td class="num font-semibold">{row.points}</td>
						<td class="num rate">{formatRate(row.win_rate)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if !compact}
		<div class="lineups">
			{#each standings as row (row.team_id)}
				<div class="lineup">
					<span class="lineup-team">{row.name}</span>
					<span class="lineup-names">
						{#each row.members as member, i (member.player_id)}
							{#if playerHref}
								<a class="pl" href={playerHref(member.player_id)}>{member.name}</a>
							{:else}
								<span class="pl">{member.name}</span>
							{/if}{#if i < row.members.length - 1}<span class="sep">·</span><wbr />{/if}
						{/each}
					</span>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.scroll {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}
	.table :global(th),
	.table :global(td) {
		white-space: nowrap;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.rate {
		color: var(--ink-primary);
		font-weight: 600;
	}
	.team-col {
		text-align: left;
		min-width: 7rem;
	}
	.team-name {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-weight: 600;
	}
	tr.champion {
		background: color-mix(in oklch, var(--color-primary) 9%, transparent);
	}
	.lineups {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 14px;
		padding-top: 12px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
	}
	.lineup {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 8px;
		font-size: 0.8rem;
		line-height: 1.5;
	}
	.lineup-team {
		font-weight: 700;
		min-width: 5.5rem;
	}
	.lineup-names {
		color: color-mix(in oklch, var(--color-base-content) 78%, transparent);
	}
	.sep {
		margin: 0 4px;
		opacity: 0.45;
	}
	a.pl:hover {
		color: var(--ink-primary);
		text-decoration: underline;
	}
</style>
