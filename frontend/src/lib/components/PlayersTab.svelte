<script>
	import PlayerComparisons from './PlayerComparisons.svelte';
	import PlayerLeaders from './PlayerLeaders.svelte';
	import PlayerStreaks from './PlayerStreaks.svelte';

	/**
	 * @type {{
	 *   stats: import('$lib/types.js').Stats,
	 *   evolution: import('$lib/types.js').Evolution,
	 *   view: ReturnType<typeof import('$lib/groupView.svelte.js').createGroupView<any>>,
	 *   playerHref: (playerId: number) => string,
	 *   before?: import('svelte').Snippet
	 * }}
	 */
	let {
		stats,
		evolution,
		view,
		playerHref,
		before
	} = $props();

	const STREAK_PREFIX = 'streak-';
	const streakFocused = $derived(view.focus?.startsWith(STREAK_PREFIX) ?? false);
</script>

<div class="flex flex-col gap-4">
	{@render before?.()}
	{#if !streakFocused}
		<PlayerLeaders
			ranking={stats.ranking}
			previousRanking={stats.previous_ranking}
			minMatchdays={stats.min_matchdays}
			{playerHref}
			focus={view.focus}
			unit={view.unit}
			onFocus={view.setFocus}
			onUnit={view.setUnit}
		/>
	{/if}
	{#if !view.focus || streakFocused}
		<PlayerStreaks
			ranking={stats.ranking}
			minMatchdays={stats.min_matchdays}
			{playerHref}
			focus={view.focus}
			onFocus={view.setFocus}
		/>
	{/if}
	<PlayerComparisons
		{evolution}
		minMatchdays={stats.min_matchdays}
		unit={view.unit}
		onUnit={view.setUnit}
	/>
</div>
