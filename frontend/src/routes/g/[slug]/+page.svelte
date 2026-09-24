<script>
	import { publicErrorMessage } from '$lib/publicApi.js';
	import { page } from '$app/stores';
	import { get } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import { setGroupTracking } from '$lib/tracking.svelte.js';
	import GroupStats from '$lib/components/GroupStats.svelte';
	import PlayersTab from '$lib/components/PlayersTab.svelte';
	import RankingTab from '$lib/components/RankingTab.svelte';
	import TimelineCharts from '$lib/components/TimelineCharts.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { createGroupView } from '$lib/groupView.svelte.js';

	/** @type {{ data: { group: import('$lib/types.js').PublicGroup|null, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	const token = $derived($page.url.searchParams.get('t'));

	setGroupTracking(() => group);
	const slug = $derived(/** @type {string} */ ($page.params.slug));

	const error = $derived(publicErrorMessage(data.status));

	const view = createGroupView({
		tabIds: ['ranking', 'players', 'stats', 'matchdays'],
		defaultTab: 'ranking'
	});

	const tabs = $derived([
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'matchdays', label: t('tab.matchdays') }
	]);

	/** @param {number} playerId */
	const playerHref = (playerId) =>
		`/g/${slug}/players/${playerId}${token ? `?t=${encodeURIComponent(token)}` : ''}`;

	const tokenQuery = $derived(token ? `t=${encodeURIComponent(token)}` : '');

	let pairs = $state(/** @type {import('$lib/types.js').PairLeaderboard|null} */ (null));
	let network = $state(/** @type {import('$lib/types.js').AssistNetwork|null} */ (null));
	let timeline = $state(/** @type {import('$lib/types.js').Timeline|null} */ (null));
	let minDays = $state(3);

	const base = $derived(`/public/${encodeURIComponent(slug)}`);
	const tokenSuffix = $derived(tokenQuery ? `?${tokenQuery}` : '');

	$effect(() => {
		const root = base;
		const suffix = tokenSuffix;
		if (!group) return;
		let current = true;
		Promise.all([get(`${root}/assist-network${suffix}`), get(`${root}/timeline${suffix}`)])
			.then(([n, tl]) => {
				if (!current) return;
				network = n;
				timeline = tl;
			})
			.catch(() => {
				if (!current) return;
				network = null;
				timeline = null;
			});
		return () => {
			current = false;
		};
	});

	$effect(() => {
		const root = base;
		const days = minDays;
		const query = [tokenQuery, `min_days=${days}`].filter(Boolean).join('&');
		if (!group) return;
		let current = true;
		get(`${root}/pairs?${query}`)
			.then((p) => current && (pairs = p))
			.catch(() => current && (pairs = null));
		return () => {
			current = false;
		};
	});

	const title = $derived(group ? t('title.public', { name: group.name }) : t('title.home'));
	const metaDescription = $derived.by(() => {
		if (!group) return '';
		const counts = t('public.metaCounts', {
			matchdays: t('group.matchdayCount', { count: group.stats.total_matchdays }),
			players: t('group.playerCount', { count: group.stats.ranking.length })
		});
		return [group.description, counts, t('public.metaTagline')].filter(Boolean).join(' · ');
	});
	const shareUrl = $derived($page.url.origin + $page.url.pathname);
</script>

<svelte:head>
	<title>{title}</title>
	{#if group}
		<meta name="description" content={metaDescription} />
		<meta property="og:type" content="website" />
		<meta property="og:site_name" content="Peladex" />
		<meta property="og:title" content={title} />
		<meta property="og:description" content={metaDescription} />
		<meta property="og:url" content={shareUrl} />
	{/if}
	{#if token}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

{#if error}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">{error}</div>
{:else if group}
	<div class="head">
		<span class="badge badge-soft badge-primary">
			<Icon name="ball" />
			{t('public.badge')}
		</span>
		<h1 class="text-[2rem] font-semibold tracking-tight">{group.name}</h1>
		{#if group.description}<p class="text-base-content/80">{group.description}</p>{/if}
	</div>

	<TabBar
		{tabs}
		active={view.tab}
		onChange={view.setTab}
		label={t('tab.sections')}
		controls="public-panel"
		idPrefix="ptab"
		center
	/>

	<div
		id="public-panel"
		class="panel"
		role="tabpanel"
		aria-labelledby={`ptab-${view.tab}`}
		bind:this={view.panel}
	>
		{#if view.tab === 'ranking'}
			<RankingTab stats={group.stats} matchdays={group.matchdays} {view} {playerHref} />
		{:else if view.tab === 'players'}
			<PlayersTab
				stats={group.stats}
				evolution={group.evolution}
				{pairs}
				{network}
				{minDays}
				onMinDays={(value) => (minDays = value)}
				{view}
				{playerHref}
				analysisHref={`/g/${slug}/analise${tokenQuery ? `?${tokenQuery}` : ''}`}
			/>
		{:else if view.tab === 'stats'}
			<div class="flex flex-col gap-4">
				<GroupStats stats={group.stats} />
				{#if timeline}
					<TimelineCharts {timeline} />
				{/if}
			</div>
		{:else if view.tab === 'matchdays'}
			<MatchdaysList matchdays={group.matchdays} showMismatch={false} {playerHref} />
		{/if}
	</div>
{/if}

<style>
	.panel {
		scroll-margin-top: 80px;
	}
	.head {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		text-align: center;
		margin-bottom: 24px;
	}
</style>
