<script>
	import { periodParam, periodQuery, publicErrorMessage } from '$lib/publicApi.js';
	import { page } from '$app/stores';
	import { get } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import { setGroupTracking } from '$lib/tracking.svelte.js';
	import GroupStats from '$lib/components/GroupStats.svelte';
	import CombosTab from '$lib/components/CombosTab.svelte';
	import PlayersTab from '$lib/components/PlayersTab.svelte';
	import RankingTab from '$lib/components/RankingTab.svelte';
	import TimelineCharts from '$lib/components/TimelineCharts.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import PublicGroupHeader from '$lib/components/PublicGroupHeader.svelte';
	import { publicTabs } from '$lib/groupTabs.js';
	import DayTypeFilter from '$lib/components/DayTypeFilter.svelte';
	import PeriodFilter from '$lib/components/PeriodFilter.svelte';
	import { dayTypeParam, dayTypeQuery, withDayType, setDayTypeContext } from '$lib/dayType.js';
	import { createGroupView, replaceParams } from '$lib/groupView.svelte.js';

	/** @type {{ data: { group: import('$lib/types.js').PublicGroup|null, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	const hasGroup = $derived(!!group);
	const token = $derived($page.url.searchParams.get('t'));

	setGroupTracking(() => group);
	setDayTypeContext(() => group?.stats.days);
	const slug = $derived(/** @type {string} */ ($page.params.slug));

	const error = $derived(publicErrorMessage(data.status));

	const view = createGroupView({
		tabIds: ['ranking', 'players', 'combos', 'stats', 'matchdays'],
		defaultTab: 'ranking'
	});

	const tabs = $derived(publicTabs());

	const dayType = $derived(dayTypeParam($page.url.searchParams));
	const period = $derived(periodParam($page.url.searchParams));

	/** @param {number} playerId */
	const playerHref = (playerId) =>
		withDayType(
			`/g/${slug}/players/${playerId}${token ? `?t=${encodeURIComponent(token)}` : ''}`,
			dayType
		);

	const tokenQuery = $derived(token ? `t=${encodeURIComponent(token)}` : '');

	const players = $derived([
		...new Map(
			(group?.matchdays ?? [])
				.flatMap((matchday) => matchday.standings.flatMap((standing) => standing.members))
				.map((member) => [member.player_id, { id: member.player_id, name: member.name }])
		).values()
	]);

	const viewQuery = $derived([tokenQuery, dayTypeQuery(dayType)].filter(Boolean).join('&'));
	const filterQuery = $derived([viewQuery, periodQuery(period)].filter(Boolean).join('&'));

	let timeline = $state(/** @type {import('$lib/types.js').Timeline|null} */ (null));

	const base = $derived(`/public/${encodeURIComponent(slug)}`);
	const filterSuffix = $derived(filterQuery ? `?${filterQuery}` : '');

	$effect(() => {
		const root = base;
		const suffix = filterSuffix;
		if (!hasGroup) return;
		let current = true;
		get(`${root}/timeline${suffix}`)
			.then((tl) => {
				if (current) timeline = tl;
			})
			.catch(() => {
				if (current) timeline = null;
			});
		return () => {
			current = false;
		};
	});

	const title = $derived(group ? t('title.public', { name: group.name }) : t('title.home'));
	const metaDescription = $derived.by(() => {
		if (!group) return '';
		const counts = t('public.metaCounts', {
			matchdays: t('group.matchdayCount', { count: group.matchdays.length }),
			players: t('group.playerCount', { count: group.stats.ranking.length })
		});
		return [group.description, counts, t('public.metaTagline')].filter(Boolean).join(' · ');
	});
	const shareUrl = $derived($page.url.origin + $page.url.pathname);
</script>

{#snippet dayTypeBar()}
	{#if group}
		<DayTypeFilter
			days={group.stats.days}
			onchange={(value) => replaceParams({ day_type: value })}
		/>
	{/if}
{/snippet}

{#snippet periodBar()}
	{@render dayTypeBar()}
	<div class="card bg-base-100 p-4">
		<PeriodFilter
			from={period.from}
			to={period.to}
			onchange={(range) =>
				replaceParams({ date_from: range.from || null, date_to: range.to || null })}
		/>
	</div>
{/snippet}

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
	<PublicGroupHeader name={group.name} description={group.description} />

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
			<RankingTab
				stats={group.stats}
				{view}
				{playerHref}
				before={periodBar}
			/>
		{:else if view.tab === 'players'}
			<PlayersTab
				stats={group.stats}
				evolution={group.evolution}
				{view}
				{playerHref}
				before={periodBar}
			/>
		{:else if view.tab === 'combos'}
			<CombosTab
				root={base}
				access={tokenQuery}
				ranking={group.stats.ranking}
				{players}
				{period}
				{dayType}
				{playerHref}
				before={periodBar}
			/>
		{:else if view.tab === 'stats'}
			<div class="flex flex-col gap-4">
				{@render periodBar()}
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
</style>
