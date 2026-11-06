<script>
	import RankingTable from './RankingTable.svelte';

	/**
	 * @type {{
	 *   stats: import('$lib/types.js').Stats,
	 *   view: ReturnType<typeof import('$lib/groupView.svelte.js').createGroupView<any>>,
	 *   playerHref: (playerId: number) => string,
	 *   before?: import('svelte').Snippet
	 * }}
	 */
	let { stats, view, playerHref, before } = $props();
</script>

<div class="flex flex-col gap-4">
	{@render before?.()}
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
