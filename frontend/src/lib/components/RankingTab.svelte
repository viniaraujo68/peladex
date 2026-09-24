<script>
	import LastMatchdaySummary from './LastMatchdaySummary.svelte';
	import RankingTable from './RankingTable.svelte';

	/**
	 * @type {{
	 *   stats: import('$lib/types.js').Stats,
	 *   matchdays: import('$lib/types.js').Matchday[],
	 *   view: ReturnType<typeof import('$lib/groupView.svelte.js').createGroupView<any>>,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { stats, matchdays, view, playerHref } = $props();
</script>

<div class="flex flex-col gap-4">
	<LastMatchdaySummary {matchdays} {playerHref} onOpenDay={() => view.setTab('matchdays')} />
	<div class="card bg-base-100 p-5">
		<RankingTable
			ranking={stats.ranking}
			previousRanking={stats.previous_ranking}
			{playerHref}
			unit={view.unit}
			onUnit={view.setUnit}
			sort={view.sort}
			onSort={view.setSort}
		/>
	</div>
</div>
