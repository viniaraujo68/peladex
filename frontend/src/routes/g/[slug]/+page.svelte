<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import AssistNetwork from '$lib/components/AssistNetwork.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import PairLeaderboard from '$lib/components/PairLeaderboard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import TabBar from '$lib/components/TabBar.svelte';

	/** @type {{ data: { group: import('$lib/types.js').PublicGroup|null, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	const token = $derived($page.url.searchParams.get('t'));
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

	const TAB_IDS = ['ranking', 'stats', 'matchdays'];
	const DEFAULT_TAB = 'ranking';
	const tab = $derived.by(() => {
		const requested = $page.url.searchParams.get('tab');
		return requested && TAB_IDS.includes(requested) ? requested : DEFAULT_TAB;
	});

	const tabs = $derived([
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'matchdays', label: t('tab.matchdays') }
	]);

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
	let minDays = $state(3);

	$effect(() => {
		const days = minDays;
		const base = `/public/${encodeURIComponent(slug)}`;
		/** @param {string} extra */
		const join = (extra) => [tokenQuery, extra].filter(Boolean).join('&');
		if (!group) return;
		Promise.all([
			get(`${base}/pairs?${join(`min_days=${days}`)}`),
			get(`${base}/assist-network${tokenQuery ? `?${tokenQuery}` : ''}`)
		])
			.then(([p, n]) => {
				pairs = p;
				network = n;
			})
			.catch(() => {
				pairs = null;
				network = null;
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
			<div class="card bg-base-100 p-5">
				<RankingTable ranking={group.stats.ranking} {playerHref} />
			</div>
		{:else if tab === 'stats'}
			<div class="flex flex-col gap-4">
				<Records records={group.stats.records} stats={group.stats} />
				<div class="card flex flex-col gap-4 bg-base-100 p-5">
					<div>
						<h3 class="font-semibold">{t('stats.evolution')}</h3>
						<p class="mt-1 text-xs text-base-content/65">{t('stats.evolutionHint')}</p>
					</div>
					<EvolutionChart evolution={group.evolution} />
				</div>

				{#if pairs}
					<PairLeaderboard
						board={pairs}
						{minDays}
						onMinDays={(value) => (minDays = value)}
						{playerHref}
					/>
				{/if}

				{#if network && group.stats.total_assists > 0}
					<AssistNetwork {network} {playerHref} />
				{/if}

				<a
					href={`/g/${slug}/analise${tokenQuery ? `?${tokenQuery}` : ''}`}
					class="btn self-start"
				>
					{t('stats.openAnalysis')}
				</a>
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
