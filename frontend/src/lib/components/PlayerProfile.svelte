<script>
	import {
		formatContribution,
		formatNote,
		formatNumber,
		formatRate,
		formatShortDate
	} from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';

	const tracking = getTracking();
	import Icon from './Icon.svelte';
	import ComboExplorer from './ComboExplorer.svelte';
	import FormDots from './FormDots.svelte';
	import RankMove from './RankMove.svelte';
	import PairList from './PairList.svelte';
	import PlayerCharts from './PlayerCharts.svelte';

	/**
	 * @type {{
	 *   detail: import('$lib/types.js').PlayerDetail,
	 *   evolution: import('$lib/types.js').Evolution,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   playerHref?: (playerId: number) => string,
	 *   players?: { id: number, name: string }[],
	 *   compareHref?: string,
	 *   runCombo?: ((body: any) => Promise<import('$lib/types.js').ComboResult>)|null
	 * }}
	 */
	let {
		detail,
		evolution,
		minDays,
		onMinDays,
		playerHref,
		players = [],
		compareHref = '',
		runCombo = null
	} = $props();

	const summary = $derived(detail.summary);
	const showGoals = $derived(tracking.trackScorers);
	const showAssists = $derived(tracking.trackScorers && tracking.trackAssists);
	const rating = $derived(tracking.showRatings ? detail.rating : null);

	/** @param {import('$lib/types.js').RatingComponent} component */
	function componentHint(component) {
		const format = ['results', 'mvp'].includes(component.code) ? formatRate : formatNumber;
		const key =
			component.code === 'scoring' && !showAssists
				? 'rating.scoringGoalsHint'
				: `rating.${component.code}Hint`;
		return t(key, {
			rate: format(component.rate),
			group: format(component.group_rate),
			goals: summary.goals,
			assists: summary.assists,
			matches: summary.matches
		});
	}
</script>

<div class="profile">
	<section class="tiles">
		<div class="tile">
			<span class="tl">{t('ranking.winRate')}</span>
			<span class="tv primary">{formatRate(summary.win_rate)}</span>
			<span class="ts">
				{t('short.points', { count: summary.points })} ·
				{t('short.matches', { count: summary.matches })}
			</span>
			{#if summary.rank !== null}
				<span class="ts">
					{t('player.rankOf', { rank: summary.rank })}
					<RankMove rank={summary.rank} previous={summary.previous_rank} />
				</span>
			{/if}
			{#if !summary.qualified}
				<span class="ts">{t('player.notQualified')}</span>
			{/if}
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.matchdays')}</span>
			<span class="tv">{summary.matchdays}</span>
			<span class="ts">{summary.wins}V · {summary.draws}E · {summary.losses}D</span>
			<span class="ts">
				{t('player.matchesPerDay', { value: formatNumber(summary.matches_per_matchday) })}
			</span>
		</div>
		{#if showGoals}
		<div class="tile">
			<span class="tl">{t('ranking.goals')}</span>
			<span class="tv">{summary.goals}</span>
			<span class="ts">
				{t('player.perMatch', { value: formatNumber(summary.goals_per_match) })}
				· {t('player.perDay', { value: formatNumber(summary.goals_per_matchday) })}
			</span>
			{#if summary.goals > 0}
				<span class="ts">
					{t('player.goalEvery', { value: formatNumber(summary.matches / summary.goals) })}
				</span>
			{/if}
		</div>
		<div class="tile">
			<span class="tl">{t('player.goalShare')}</span>
			<span class="tv">{formatRate(summary.goal_share)}</span>
			<span class="ts">
				{t('player.shareOf', { value: summary.goals, total: summary.team_goals })}
			</span>
		</div>
		{/if}
		{#if showAssists}
			<div class="tile">
				<span class="tl">{t('ranking.assists')}</span>
				<span class="tv">{summary.assists}</span>
				<span class="ts">
					{t('player.perMatch', { value: formatNumber(summary.assists_per_match) })}
					· {t('player.contributions')}: {summary.contributions}
				</span>
			</div>
			<div class="tile">
				<span class="tl">{t('player.assistShare')}</span>
				<span class="tv">{formatRate(summary.assist_share)}</span>
				<span class="ts">
					{t('player.shareOf', { value: summary.assists, total: summary.team_goals })}
				</span>
			</div>
		{/if}
		<div class="tile">
			<span class="tl">{t('ranking.titles')}</span>
			<span class="tv">{summary.titles}</span>
			<span class="ts">{formatRate(summary.title_rate)}</span>
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.mvp')}</span>
			<span class="tv">{summary.mvp_count}</span>
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.form')}</span>
			<span class="tv">{formatRate(summary.recent_win_rate)}</span>
			<FormDots form={summary.recent_form} />
			<span class="ts">
				{t('ranking.presence')} {formatRate(summary.presence)}
			</span>
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.streak')}</span>
			<span class="tv">{summary.title_streak}</span>
			<span class="ts">
				{t('records.most_titles')}: {t('ranking.streakValue', {
					count: summary.best_title_streak
				})}
			</span>
		</div>
		<div class="tile">
			<span class="tl">{t('player.runs')}</span>
			{#if showGoals}
				<span class="ts strong">
					{summary.goal_streak > 0
						? t('player.scoringRun', { count: summary.goal_streak })
						: t('player.droughtRun', { count: summary.goal_drought })}
				</span>
			{/if}
			<span class="ts strong">
				{summary.absent_matchdays > 0
					? t('player.awayRun', { count: summary.absent_matchdays })
					: t('player.presenceRun', { count: summary.presence_streak })}
			</span>
		</div>
	</section>

	{#if compareHref}
		<a class="btn btn-sm self-start" href={compareHref}>{t('player.compare')}</a>
	{/if}

	{#if rating}
		<section class="card flex flex-col gap-4 bg-base-100 p-5">
			<div class="ratinghead">
				<div>
					<h3 class="font-semibold">{t('rating.title')}</h3>
					<p class="hint">{t('rating.hint')}</p>
				</div>
				<div class="note">
					<span class="notevalue">{formatNote(rating.note)}</span>
					{#if rating.provisional}
						<span class="badge badge-soft badge-warning badge-sm">{t('rating.provisional')}</span>
					{/if}
				</div>
			</div>
			{#if rating.provisional}
				<p class="hint">{t('rating.provisionalHint')}</p>
			{/if}
			<ul class="components">
				{#each rating.components as component (component.code)}
					<li class="component">
						<span class="cname">{t(`rating.${component.code}`)}</span>
						<span
							class="cvalue"
							class:up={component.contribution > 0}
							class:down={component.contribution < 0}
						>
							{formatContribution(component.contribution)}
						</span>
						<span class="chint">{componentHint(component)}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if summary.matchdays === 0}
		<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
			{t('player.noHistory')}
		</div>
	{:else}
		<PlayerCharts
			playerId={detail.player_id}
			playerName={detail.name}
			{evolution}
			history={detail.history}
		/>

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<div class="pairhead">
				<p class="caveat">{t('player.pairCaveat', { count: minDays })}</p>
				<label class="mindays">
					<span>{t('player.minDays')}</span>
					<input
						class="input input-sm"
						type="number"
						min="1"
						max="50"
						value={minDays}
						onchange={(e) => onMinDays(Number(e.currentTarget.value) || 1)}
					/>
				</label>
			</div>
		</section>

		<div class="pairs">
			<PairList
				rows={detail.partners}
				title={t('player.partners')}
				hint={t('player.partnersHint2')}
				rateLabel={t('player.rateTogether')}
				rateWithoutLabel={t('player.rateWithout')}
				peerLabel={t('player.teammate')}
				{minDays}
				{playerHref}
			/>
			<PairList
				rows={detail.opponents}
				title={t('player.opponents')}
				hint={t('player.opponentsHint2')}
				rateLabel={t('player.rateAgainst')}
				rateWithoutLabel={t('player.rateAgainstWithout')}
				peerLabel={t('player.opponent')}
				{minDays}
				{playerHref}
			/>
		</div>

		{#if runCombo && players.length > 1}
			<section class="card flex flex-col gap-3 bg-base-100 p-5">
				<div>
					<h3 class="font-semibold">{t('player.myCombos')}</h3>
					<p class="hint">{t('player.myCombosHint')}</p>
				</div>
				<ComboExplorer
					{players}
					run={runCombo}
					locked={{ id: detail.player_id, name: detail.name }}
					compact
				/>
			</section>
		{/if}

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<h3 class="font-semibold">{t('player.history')}</h3>
			<div class="scroll">
				<table class="table table-sm">
					<thead>
						<tr>
							<th>{t('day.date')}</th>
							<th>{t('standings.team')}</th>
							<th class="num">{t('player.position')}</th>
							<th class="num">{t('standings.played')}</th>
							<th class="num">{t('standings.wins')}</th>
							<th class="num">{t('standings.draws')}</th>
							<th class="num">{t('standings.losses')}</th>
							<th class="num">{t('ranking.winRate')}</th>
							{#if showGoals}<th class="num">{t('ranking.goals')}</th>{/if}
							{#if showAssists}<th class="num">{t('ranking.assists')}</th>{/if}
						</tr>
					</thead>
					<tbody>
						{#each detail.history as row (row.matchday_id)}
							<tr>
								<td class="whitespace-nowrap">
									{formatShortDate(row.date)}
									{#if row.mvp}
										<span class="tag mvp" title={t('player.mvpBadge')}>
											<Icon name="star" class="size-3" />
										</span>
									{/if}
								</td>
								<td class="font-medium">
									{row.team_name}
									{#if row.champion}
										<span class="tag champ" title={t('player.championBadge')}>
											<Icon name="trophy" class="size-3" />
										</span>
									{/if}
								</td>
								<td class="num muted">
									{t('player.positionOf', { position: row.position, teams: row.teams })}
								</td>
								<td class="num">{row.played}</td>
								<td class="num">{row.wins}</td>
								<td class="num">{row.draws}</td>
								<td class="num">{row.losses}</td>
								<td class="num rate">{formatRate(row.win_rate)}</td>
								{#if showGoals}<td class="num">{row.goals || ''}</td>{/if}
								{#if showAssists}<td class="num">{row.assists || ''}</td>{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>

<style>
	.ratinghead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
	}
	.note {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.notevalue {
		font-size: 2rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
		color: var(--ink-primary);
	}
	.components {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.component {
		display: grid;
		grid-template-columns: 8.5rem 4rem 1fr;
		align-items: baseline;
		gap: 10px;
		font-size: 0.84rem;
	}
	.cname {
		font-weight: 600;
	}
	.cvalue {
		text-align: right;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--ink-muted);
	}
	.cvalue.up {
		color: var(--color-success);
	}
	.cvalue.down {
		color: var(--color-error);
	}
	.chint {
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	@media (max-width: 560px) {
		.component {
			grid-template-columns: 1fr auto;
		}
		.chint {
			grid-column: 1 / -1;
		}
	}
	.profile {
		display: flex;
		flex-direction: column;
		gap: 16px;
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
		padding: 14px 16px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		border-radius: var(--radius-box);
		background: var(--color-base-100);
	}
	.tl {
		font-size: 0.66rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.tv {
		font-size: 1.55rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
	.tv.primary {
		color: var(--ink-primary);
	}
	.ts {
		font-size: 0.72rem;
		color: var(--ink-muted);
		font-variant-numeric: tabular-nums;
	}
	.ts.strong {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-base-content);
	}
	.pairhead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
	}
	.caveat {
		flex: 1 1 260px;
		font-size: 0.78rem;
		line-height: 1.5;
		color: var(--ink-muted);
	}
	.mindays {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.mindays input {
		width: 4.5rem;
	}
	.hint {
		margin-top: 3px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.pairs {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
		gap: 16px;
	}
	.scroll {
		overflow-x: auto;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.muted {
		color: var(--ink-muted);
	}
	.rate {
		font-weight: 600;
		color: var(--ink-primary);
	}
	.tag {
		display: inline-flex;
		align-items: center;
		margin-left: 4px;
	}
	.tag.champ {
		color: var(--ink-primary);
	}
	.tag.mvp {
		color: var(--ink-warning);
	}
</style>
