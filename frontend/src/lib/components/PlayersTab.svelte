<script>
	import { t } from '$lib/i18n.svelte.js';
	import PlayerComparisons from './PlayerComparisons.svelte';
	import PlayerLeaders from './PlayerLeaders.svelte';
	import PlayerStreaks from './PlayerStreaks.svelte';

	/**
	 * @type {{
	 *   stats: import('$lib/types.js').Stats,
	 *   evolution: import('$lib/types.js').Evolution,
	 *   pairs: import('$lib/types.js').PairLeaderboard|null,
	 *   network: import('$lib/types.js').AssistNetwork|null,
	 *   minDays: number,
	 *   onMinDays: (value: number) => void,
	 *   view: ReturnType<typeof import('$lib/groupView.svelte.js').createGroupView<any>>,
	 *   playerHref: (playerId: number) => string,
	 *   analysisHref: string,
	 *   before?: import('svelte').Snippet
	 * }}
	 */
	let {
		stats,
		evolution,
		pairs,
		network,
		minDays,
		onMinDays,
		view,
		playerHref,
		analysisHref,
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
		{pairs}
		{network}
		{minDays}
		{onMinDays}
		minMatchdays={stats.min_matchdays}
		unit={view.unit}
		onUnit={view.setUnit}
		{playerHref}
	/>
	<a href={analysisHref} class="btn self-start">{t('stats.openAnalysis')}</a>
</div>
