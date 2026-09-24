<script>
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { confirm } from '@viniaraujo68/plinth/confirm';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { del, get, errorMessage, errorStatus } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatMatchdayDate } from '$lib/format.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { mismatchBadgeEnabled } from '$lib/prefs.svelte.js';
	import { setGroupTracking } from '$lib/tracking.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import GroupStats from '$lib/components/GroupStats.svelte';
	import PeriodFilter from '$lib/components/PeriodFilter.svelte';
	import PlayersTab from '$lib/components/PlayersTab.svelte';
	import RankingTab from '$lib/components/RankingTab.svelte';
	import TimelineCharts from '$lib/components/TimelineCharts.svelte';
	import GroupSettings from '$lib/components/GroupSettings.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { createGroupView } from '$lib/groupView.svelte.js';

	const groupId = $derived(/** @type {string} */ ($page.params.id));

	setGroupTracking(() => group);

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let matchdays = $state(/** @type {import('$lib/types.js').Matchday[]} */ ([]));
	let stats = $state(/** @type {import('$lib/types.js').Stats|null} */ (null));
	let evolution = $state(/** @type {import('$lib/types.js').Evolution|null} */ (null));
	let pairs = $state(/** @type {import('$lib/types.js').PairLeaderboard|null} */ (null));
	let network = $state(/** @type {import('$lib/types.js').AssistNetwork|null} */ (null));
	let timeline = $state(/** @type {import('$lib/types.js').Timeline|null} */ (null));
	let loading = $state(true);
	let error = $state('');
	let period = $state({ from: '', to: '' });
	let minDays = $state(3);

	const periodQuery = $derived(
		[
			period.from ? `date_from=${period.from}` : '',
			period.to ? `date_to=${period.to}` : ''
		]
			.filter(Boolean)
			.join('&')
	);

	const TAB_IDS = ['matchdays', 'ranking', 'players', 'stats', 'settings'];
	const view = createGroupView({ tabIds: TAB_IDS, defaultTab: 'matchdays' });

	const tabs = $derived([
		{ id: 'matchdays', label: t('tab.matchdays') },
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'settings', label: t('tab.settings') }
	]);

	const showMismatchBadge = $derived(group ? mismatchBadgeEnabled(group.id) : false);
	const mismatchCount = $derived(matchdays.filter((m) => m.goal_mismatch).length);

	/** @param {number} playerId */
	const playerHref = (playerId) => `/groups/${groupId}/players/${playerId}`;

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) loadAll();
	});

	async function loadAll() {
		loading = true;
		error = '';
		try {
			[group, matchdays] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/matchdays`)
			]);
			await loadAnalysis();
		} catch (e) {
			error = errorStatus(e) === 403 ? t('group.accessDenied') : errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/** @param {string} query */
	function fetchPeriod(query) {
		const suffix = query ? `?${query}` : '';
		return Promise.all([
			get(`/groups/${groupId}/stats${suffix}`),
			get(`/groups/${groupId}/evolution${suffix}`),
			get(`/groups/${groupId}/assist-network${suffix}`),
			get(`/groups/${groupId}/timeline${suffix}`)
		]);
	}

	/** @param {string} query @param {number} days */
	function fetchPairs(query, days) {
		return get(`/groups/${groupId}/pairs?${[`min_days=${days}`, query].filter(Boolean).join('&')}`);
	}

	async function loadAnalysis() {
		const [[s, e, n, tl], p] = await Promise.all([
			fetchPeriod(periodQuery),
			fetchPairs(periodQuery, minDays)
		]);
		[stats, evolution, network, timeline, pairs] = [s, e, n, tl, p];
	}

	/** @param {unknown} e */
	const refreshFailed = (e) =>
		toast.error(t('group.refreshFailed', { message: errorMessage(e) }));

	const ready = () => Boolean(groupId && auth.user) && untrack(() => stats !== null);

	$effect(() => {
		const query = periodQuery;
		if (!ready()) return;
		let current = true;
		fetchPeriod(query)
			.then(([s, e, n, tl]) => {
				if (!current) return;
				[stats, evolution, network, timeline] = [s, e, n, tl];
			})
			.catch((e) => current && refreshFailed(e));
		return () => {
			current = false;
		};
	});

	$effect(() => {
		const query = periodQuery;
		const days = minDays;
		if (!ready()) return;
		let current = true;
		fetchPairs(query, days)
			.then((p) => current && (pairs = p))
			.catch((e) => current && refreshFailed(e));
		return () => {
			current = false;
		};
	});

	async function refreshData() {
		try {
			matchdays = await get(`/groups/${groupId}/matchdays`);
			await loadAnalysis();
		} catch (e) {
			toast.error(t('group.refreshFailed', { message: errorMessage(e) }));
		}
	}

	/** @param {import('$lib/types.js').Group} [updated] */
	function onGroupChange(updated) {
		if (updated) group = group ? { ...group, ...updated } : updated;
		refreshData();
	}

	/** @param {import('$lib/types.js').Matchday} matchday */
	async function deleteMatchday(matchday) {
		const confirmed = await confirm({
			title: t('day.deleteTitle', { date: formatMatchdayDate(matchday.date) }),
			description: t('day.deleteBody'),
			confirmLabel: t('common.delete'),
			danger: true
		});
		if (!confirmed) return;
		try {
			await del(`/groups/${groupId}/matchdays/${matchday.id}`);
		} catch (e) {
			toast.error(t('day.deleteFailed', { message: errorMessage(e) }));
			return;
		}
		toast.success(t('toast.matchdayDeleted'));
		await refreshData();
	}
</script>

{#snippet periodBar()}
	<div class="card bg-base-100 p-4">
		<PeriodFilter from={period.from} to={period.to} onchange={(range) => (period = range)} />
	</div>
{/snippet}

<svelte:head>
	<title>{group ? t('title.group', { name: group.name }) : t('title.home')}</title>
</svelte:head>

{#if loading}
	<div class="flex flex-col gap-4" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<Skeleton class="h-[30px] w-[min(280px,70%)]" />
		<Skeleton class="mb-2 h-3 w-[min(200px,50%)]" />
		<div class="mb-2 flex gap-1 border-b border-base-content/10 pb-2.5">
			{#each TAB_IDS as id (id)}<Skeleton class="h-[18px] w-[72px]" />{/each}
		</div>
		{#each [0, 1, 2] as i (i)}
			<div class="card flex flex-col gap-2.5 bg-base-100 p-4">
				<Skeleton class="h-4 w-2/5" />
				<div class="flex gap-1.5">
					<Skeleton class="h-[22px] w-[68px]" rounded="full" />
					<Skeleton class="h-[22px] w-[68px]" rounded="full" />
					<Skeleton class="h-[22px] w-[68px]" rounded="full" />
				</div>
			</div>
		{/each}
	</div>
{:else if error}
	<div class="alert alert-soft alert-error">{error}</div>
	<a href="/" class="btn mt-4">{t('group.back')}</a>
{:else if group && stats && evolution}
	<div class="head flex items-start justify-between gap-3">
		<div>
			<a href="/" class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content">
				{t('group.back')}
			</a>
			<h1 class="text-2xl font-semibold tracking-tight">{group.name}</h1>
			{#if group.description}<p class="mt-1 text-base-content/80">{group.description}</p>{/if}
		</div>
		<div class="headbtns flex gap-2">
			<a href={`/groups/${groupId}/matchdays/import`} class="btn">{t('group.importText')}</a>
			<a href={`/groups/${groupId}/matchdays/new`} class="btn btn-primary">
				{t('group.newMatchday')}
			</a>
		</div>
	</div>

	<TabBar
		{tabs}
		active={view.tab}
		onChange={view.setTab}
		label={t('tab.sections')}
		controls="group-panel"
	/>

	{#if showMismatchBadge && mismatchCount > 0}
		{#if view.tab === 'matchdays'}
			<span class="badge badge-soft badge-warning warn">
				<Icon name="warning" />
				{t('group.mismatch', { count: mismatchCount })}
			</span>
		{:else}
			<button
				class="badge badge-soft badge-warning warn tappable"
				title={t('group.mismatchGoTo')}
				onclick={() => view.setTab('matchdays')}
			>
				<Icon name="warning" />
				{t('group.mismatch', { count: mismatchCount })}
			</button>
		{/if}
	{/if}

	<div
		id="group-panel"
		class="panel"
		role="tabpanel"
		aria-labelledby={`tab-${view.tab}`}
		bind:this={view.panel}
	>
		{#if view.tab === 'matchdays'}
			<MatchdaysList
				{matchdays}
				editable
				showMismatch={showMismatchBadge}
				newHref={`/groups/${groupId}/matchdays/new`}
				importHref={`/groups/${groupId}/matchdays/import`}
				{playerHref}
				onEdit={(m) => goto(`/groups/${groupId}/matchdays/new?edit=${m.id}`)}
				onDelete={deleteMatchday}
			/>
		{:else if view.tab === 'ranking'}
			<RankingTab {stats} {matchdays} {view} {playerHref} />
		{:else if view.tab === 'players'}
			<PlayersTab
				{stats}
				{evolution}
				{pairs}
				{network}
				{minDays}
				onMinDays={(value) => (minDays = value)}
				{view}
				{playerHref}
				analysisHref={`/groups/${groupId}/analise`}
				before={periodBar}
			/>
		{:else if view.tab === 'stats'}
			<div class="flex flex-col gap-4">
				{@render periodBar()}
				<GroupStats {stats} />
				{#if timeline}
					<TimelineCharts {timeline} />
				{/if}
			</div>
		{:else if view.tab === 'settings'}
			<GroupSettings {group} onchange={onGroupChange} />
		{/if}
	</div>
{/if}

<style>
	.panel {
		scroll-margin-top: 80px;
	}
	.head {
		margin-bottom: 20px;
	}
	@media (max-width: 640px) {
		.head {
			flex-direction: column;
			align-items: stretch;
			gap: 12px;
		}
		.headbtns :global(.btn) {
			flex: 1;
		}
	}
	.warn {
		display: inline-flex;
		align-items: flex-start;
		height: auto;
		margin: -14px 0 20px;
		padding: 6px 12px;
		font-size: 0.8rem;
		text-align: left;
		line-height: 1.35;
		white-space: normal;
		max-width: 100%;
	}
	@media (max-width: 560px) {
		.warn {
			margin-top: -6px;
		}
	}
	.tappable {
		cursor: pointer;
	}
	.tappable:hover {
		border-color: var(--color-warning);
	}
</style>
