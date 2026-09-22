<script>
	import { formatNumber, formatRate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';

	/** @type {{ stats: import('$lib/types.js').Stats }} */
	let { stats } = $props();

	const tracking = getTracking();

	/** @param {number} total @param {number} count */
	const average = (total, count) => (count ? total / count : 0);

	const tiles = $derived([
		{ id: 'matchdays', label: t('records.totalMatchdays'), value: String(stats.total_matchdays) },
		{ id: 'matches', label: t('records.totalMatches'), value: String(stats.total_matches) },
		{ id: 'draws', label: t('stats.drawRate'), value: formatRate(stats.draw_rate) },
		{ id: 'goals', label: t('records.totalGoals'), value: String(stats.total_goals) },
		{
			id: 'goalsPerMatch',
			label: t('chart.goalsPerMatch'),
			value: formatNumber(average(stats.total_goals, stats.total_matches))
		},
		{
			id: 'goalsPerMatchday',
			label: t('chart.goalsPerMatchday'),
			value: formatNumber(average(stats.total_goals, stats.total_matchdays))
		},
		...(tracking.trackScorers && tracking.trackAssists
			? [
					{
						id: 'assists',
						label: t('records.totalAssists'),
						value: String(stats.total_assists)
					},
					{
						id: 'assistsPerMatchday',
						label: t('chart.assistsPerMatchday'),
						value: formatNumber(average(stats.total_assists, stats.total_matchdays))
					}
				]
			: [])
	]);
</script>

<div class="tiles">
	{#each tiles as tile (tile.id)}
		<div class="card flex flex-col gap-1 bg-base-100 p-4">
			<span class="tl">{tile.label}</span>
			<span class="tv">{tile.value}</span>
		</div>
	{/each}
</div>

<style>
	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 12px;
	}
	.tl {
		font-size: 0.6875rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.tv {
		font-size: 1.4rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
</style>
