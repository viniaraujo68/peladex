<script>
	import { formatNumber, formatRate, formatShortDate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';
	import PairList from './PairList.svelte';
	import PlayerCharts from './PlayerCharts.svelte';

	/**
	 * @type {{
	 *   detail: import('$lib/types.js').PlayerDetail,
	 *   evolution: import('$lib/types.js').Evolution,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   playerHref?: (playerId: number) => string
	 * }}
	 */
	let { detail, evolution, minDays, onMinDays, playerHref } = $props();

	const summary = $derived(detail.summary);
	const showAssists = $derived(
		summary.assists > 0 || detail.history.some((row) => row.assists > 0)
	);
</script>

<div class="profile">
	<section class="tiles">
		<div class="tile">
			<span class="tl">{t('ranking.winRate')}</span>
			<span class="tv primary">{formatRate(summary.win_rate)}</span>
			<span class="ts">{summary.points} pts · {summary.matches}j</span>
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.matchdays')}</span>
			<span class="tv">{summary.matchdays}</span>
			<span class="ts">{summary.wins}V · {summary.draws}E · {summary.losses}D</span>
		</div>
		<div class="tile">
			<span class="tl">{t('ranking.goals')}</span>
			<span class="tv">{summary.goals}</span>
			<span class="ts">
				{t('player.goalsPerDay', { value: formatNumber(summary.goals_per_matchday) })}
			</span>
		</div>
		{#if showAssists}
			<div class="tile">
				<span class="tl">{t('ranking.assists')}</span>
				<span class="tv">{summary.assists}</span>
				<span class="ts">{t('player.contributions')}: {summary.contributions}</span>
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
	</section>

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
				hint={t('player.partnersHint')}
				rateLabel={t('player.rateTogether')}
				peerLabel={t('player.teammate')}
				{minDays}
				{playerHref}
			/>
			<PairList
				rows={detail.opponents}
				title={t('player.opponents')}
				hint={t('player.opponentsHint')}
				rateLabel={t('player.rateAgainst')}
				peerLabel={t('player.opponent')}
				{minDays}
				{playerHref}
			/>
		</div>

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
							<th class="num">{t('ranking.goals')}</th>
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
								<td class="num">{row.goals || ''}</td>
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
	.pairs {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
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
