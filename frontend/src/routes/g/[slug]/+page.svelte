<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import { setTrackingContext } from '$lib/tracking.svelte.js';
	import GroupStats from '$lib/components/GroupStats.svelte';
	import PlayerComparisons from '$lib/components/PlayerComparisons.svelte';
	import PlayerLeaders from '$lib/components/PlayerLeaders.svelte';
	import LastMatchdaySummary from '$lib/components/LastMatchdaySummary.svelte';
	import TimelineCharts from '$lib/components/TimelineCharts.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { parseUnit } from '$lib/metrics.js';
	import { readSort, sortParams, unitParams, withParams } from '$lib/viewState.js';

	/** @type {{ data: { group: import('$lib/types.js').PublicGroup|null, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	const token = $derived($page.url.searchParams.get('t'));

	setTrackingContext({
		get trackScorers() {
			return group?.track_scorers ?? true;
		},
		get trackAssists() {
			return group?.track_assists ?? false;
		},
		get showRatings() {
			return group?.show_ratings ?? true;
		}
	});
	const slug = $derived(/** @type {string} */ ($page.params.slug));

	const error = $derived(
		data.status === 200
			? ''
			: data.status === 403
				? t('public.errorPrivate')
				: data.status === 0
					? t('error.body')
					: t('error.http', { status: data.status })
	);

	const TAB_IDS = ['ranking', 'players', 'stats', 'matchdays'];
	const DEFAULT_TAB = 'ranking';
	const tab = $derived.by(() => {
		const requested = $page.url.searchParams.get('tab');
		return requested && TAB_IDS.includes(requested) ? requested : DEFAULT_TAB;
	});

	const tabs = $derived([
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'matchdays', label: t('tab.matchdays') }
	]);

	const unit = $derived(parseUnit($page.url.searchParams.get('per')));
	const rankingSort = $derived(readSort($page.url.searchParams));
	const focus = $derived(
		/** @type {import('$lib/metrics.js').MetricId|null} */ ($page.url.searchParams.get('focus'))
	);

	/** @param {Record<string, string|null>} updates */
	function setParams(updates) {
		goto(withParams($page.url, updates), { keepFocus: true, noScroll: true, replaceState: true });
	}

	/** @param {string} id */
	function setTab(id) {
		if (id === tab) return;
		const url = new URL($page.url);
		if (id === DEFAULT_TAB) url.searchParams.delete('tab');
		else url.searchParams.set('tab', id);
		goto(url, { keepFocus: true, noScroll: true });
	}

	/** @param {number} playerId */
	const playerHref = (playerId) =>
		`/g/${slug}/players/${playerId}${token ? `?t=${encodeURIComponent(token)}` : ''}`;

	const tokenQuery = $derived(token ? `t=${encodeURIComponent(token)}` : '');

	let pairs = $state(/** @type {import('$lib/types.js').PairLeaderboard|null} */ (null));
	let network = $state(/** @type {import('$lib/types.js').AssistNetwork|null} */ (null));
	let timeline = $state(/** @type {import('$lib/types.js').Timeline|null} */ (null));
	let minDays = $state(3);

	$effect(() => {
		const days = minDays;
		const base = `/public/${encodeURIComponent(slug)}`;
		/** @param {string} extra */
		const join = (extra) => [tokenQuery, extra].filter(Boolean).join('&');
		if (!group) return;
		Promise.all([
			get(`${base}/pairs?${join(`min_days=${days}`)}`),
			get(`${base}/assist-network${tokenQuery ? `?${tokenQuery}` : ''}`),
			get(`${base}/timeline${tokenQuery ? `?${tokenQuery}` : ''}`)
		])
			.then(([p, n, tl]) => {
				pairs = p;
				network = n;
				timeline = tl;
			})
			.catch(() => {
				pairs = null;
				network = null;
				timeline = null;
			});
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
		active={tab}
		onChange={setTab}
		label={t('tab.sections')}
		controls="public-panel"
		idPrefix="ptab"
		center
	/>

	<div id="public-panel" role="tabpanel" aria-labelledby={`ptab-${tab}`}>
		{#if tab === 'ranking'}
			<div class="flex flex-col gap-4">
				<LastMatchdaySummary
					matchdays={group.matchdays}
					{playerHref}
					onOpenDay={() => setTab('matchdays')}
				/>
				<div class="card bg-base-100 p-5">
					<RankingTable
						ranking={group.stats.ranking}
						minMatchdays={group.stats.min_matchdays}
						{playerHref}
						{unit}
						onUnit={(value) => setParams(unitParams(value))}
						sort={rankingSort}
						onSort={(value) => setParams(sortParams(value))}
					/>
				</div>
			</div>
		{:else if tab === 'players'}
			<div class="flex flex-col gap-4">
				<PlayerLeaders
					ranking={group.stats.ranking}
					minMatchdays={group.stats.min_matchdays}
					{playerHref}
					{focus}
					{unit}
					onFocus={(value) => setParams({ focus: value })}
					onUnit={(value) => setParams(unitParams(value))}
				/>
				<PlayerComparisons
					evolution={group.evolution}
					{pairs}
					{network}
					{minDays}
					onMinDays={(value) => (minDays = value)}
					minMatchdays={group.stats.min_matchdays}
					{unit}
					onUnit={(value) => setParams(unitParams(value))}
					{playerHref}
				/>
				<a
					href={`/g/${slug}/analise${tokenQuery ? `?${tokenQuery}` : ''}`}
					class="btn self-start"
				>
					{t('stats.openAnalysis')}
				</a>
			</div>
		{:else if tab === 'stats'}
			<div class="flex flex-col gap-4">
				<GroupStats stats={group.stats} />
				{#if timeline}
					<TimelineCharts {timeline} />
				{/if}
			</div>
		{:else if tab === 'matchdays'}
			<MatchdaysList matchdays={group.matchdays} showMismatch={false} {playerHref} />
		{/if}
	</div>
{/if}

<style>
	.head {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		text-align: center;
		margin-bottom: 24px;
	}
</style>
