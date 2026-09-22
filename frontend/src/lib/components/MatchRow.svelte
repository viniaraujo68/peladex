<script>
	import GoalMark from './GoalMark.svelte';
	import TeamCrest from './TeamCrest.svelte';

	/**
	 * @typedef {{ key: string|number, player: string, assist?: string|null, ownGoal?: boolean }} RowGoal
	 */

	/**
	 * @type {{
	 *   homeName: string,
	 *   awayName: string,
	 *   homeScore: number,
	 *   awayScore: number,
	 *   homeColor?: string,
	 *   awayColor?: string,
	 *   homeGoals?: RowGoal[],
	 *   awayGoals?: RowGoal[],
	 *   showGoals?: boolean,
	 *   showAssist?: boolean
	 * }}
	 */
	let {
		homeName,
		awayName,
		homeScore,
		awayScore,
		homeColor = '',
		awayColor = '',
		homeGoals = [],
		awayGoals = [],
		showGoals = true,
		showAssist = false
	} = $props();
</script>

<div class="match">
	<span class="side home" class:win={homeScore > awayScore}>
		<TeamCrest name={homeName} color={homeColor} />
		<span class="tname">{homeName}</span>
	</span>
	<span class="score">{homeScore}<i>x</i>{awayScore}</span>
	<span class="side away" class:win={awayScore > homeScore}>
		<span class="tname">{awayName}</span>
		<TeamCrest name={awayName} color={awayColor} />
	</span>
	{#if showGoals && homeGoals.length + awayGoals.length > 0}
		<span class="gcol home">
			{#each homeGoals as goal (goal.key)}
				<GoalMark
					mirror
					player={goal.player}
					assist={goal.assist}
					ownGoal={goal.ownGoal}
					{showAssist}
				/>
			{/each}
		</span>
		<span class="gsep"></span>
		<span class="gcol away">
			{#each awayGoals as goal (goal.key)}
				<GoalMark
					player={goal.player}
					assist={goal.assist}
					ownGoal={goal.ownGoal}
					{showAssist}
				/>
			{/each}
		</span>
	{/if}
</div>

<style>
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
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		overflow-wrap: anywhere;
		color: var(--ink-muted);
		text-transform: uppercase;
		letter-spacing: 0.02em;
	}
	.side.home {
		justify-content: flex-end;
		text-align: right;
	}
	.side.away {
		justify-content: flex-start;
		text-align: left;
	}
	.tname {
		min-width: 0;
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
	.gcol {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-top: 4px;
		min-width: 0;
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.gcol.home {
		align-items: flex-end;
		text-align: right;
	}
	.gcol.away {
		align-items: flex-start;
		text-align: left;
	}
</style>
