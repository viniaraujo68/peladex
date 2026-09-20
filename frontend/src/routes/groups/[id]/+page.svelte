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
	import { setTrackingContext } from '$lib/tracking.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import AssistNetwork from '$lib/components/AssistNetwork.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import PairLeaderboard from '$lib/components/PairLeaderboard.svelte';
	import PeriodFilter from '$lib/components/PeriodFilter.svelte';
	import PlayersGrid from '$lib/components/PlayersGrid.svelte';
	import TimelineCharts from '$lib/components/TimelineCharts.svelte';
	import GroupSettings from '$lib/components/GroupSettings.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import MatchdaysList from '$lib/components/MatchdaysList.svelte';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import TabBar from '$lib/components/TabBar.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));

	setTrackingContext({
		get trackScorers() {
			return group?.track_scorers ?? true;
		},
		get trackAssists() {
			return group?.track_assists ?? false;
		}
	});

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let matchdays = $state(/** @type {import('$lib/types.js').Matchday[]} */ ([]));
	let stats = $state(/** @type {import('$lib/types.js').Stats|null} */ (null));
	let evolution = $state(/** @type {import('$lib/types.js').Evolution|null} */ (null));
	let pairs = $state(/** @type {import('$lib/types.js').PairLeaderboard|null} */ (null));
	let network = $state(/** @type {import('$lib/types.js').AssistNetwork|null} */ (null));
	let timeline = $state(/** @type {import('$lib/types.js').Timeline|null} */ (null));
	let metric = $state(/** @type {'win_rate'|'goals'|'assists'} */ ('win_rate'));
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
	const DEFAULT_TAB = 'matchdays';
	const tab = $derived.by(() => {
		const requested = $page.url.searchParams.get('tab');
		return requested && TAB_IDS.includes(requested) ? requested : DEFAULT_TAB;
	});

	const tabs = $derived([
		{ id: 'matchdays', label: t('tab.matchdays') },
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'settings', label: t('tab.settings') }
	]);

	/** @param {string} id */
	function setTab(id) {
		if (id === tab) return;
		const url = new URL($page.url);
		if (id === DEFAULT_TAB) url.searchParams.delete('tab');
		else url.searchParams.set('tab', id);
		goto(url, { keepFocus: true, noScroll: true });
	}

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

	/** @param {string} query @param {number} days */
	async function fetchAnalysis(query, days) {
		const suffix = query ? `?${query}` : '';
		const pairSuffix = query ? `?min_days=${days}&${query}` : `?min_days=${days}`;
		return Promise.all([
			get(`/groups/${groupId}/stats${suffix}`),
			get(`/groups/${groupId}/evolution${suffix}`),
			get(`/groups/${groupId}/pairs${pairSuffix}`),
			get(`/groups/${groupId}/assist-network${suffix}`),
			get(`/groups/${groupId}/timeline${suffix}`)
		]);
	}

	async function loadAnalysis() {
		[stats, evolution, pairs, network, timeline] = await fetchAnalysis(periodQuery, minDays);
	}

	$effect(() => {
		const query = periodQuery;
		const days = minDays;
		if (!groupId || !auth.user || untrack(() => stats === null)) return;
		fetchAnalysis(query, days)
			.then(([s, e, p, n, tl]) => {
				stats = s;
				evolution = e;
				pairs = p;
				network = n;
				timeline = tl;
			})
			.catch((e) => toast.error(t('group.refreshFailed', { message: errorMessage(e) })));
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
		else refreshData();
		if (updated) refreshData();
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

	<TabBar {tabs} active={tab} onChange={setTab} label={t('tab.sections')} controls="group-panel" />

	{#if showMismatchBadge && mismatchCount > 0}
		{#if tab === 'matchdays'}
			<span class="badge badge-soft badge-warning warn">
				<Icon name="warning" />
				{t('group.mismatch', { count: mismatchCount })}
			</span>
		{:else}
			<button
				class="badge badge-soft badge-warning warn tappable"
				title={t('group.mismatchGoTo')}
				onclick={() => setTab('matchdays')}
			>
				<Icon name="warning" />
				{t('group.mismatch', { count: mismatchCount })}
			</button>
		{/if}
	{/if}

	<div id="group-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
		{#if tab === 'matchdays'}
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
		{:else if tab === 'ranking'}
			<div class="card bg-base-100 p-5">
				<RankingTable ranking={stats.ranking} {playerHref} />
			</div>
		{:else if tab === 'players'}
			<PlayersGrid ranking={stats.ranking} {playerHref} />
		{:else if tab === 'stats'}
			<div class="flex flex-col gap-4">
				<div class="card periodbar bg-base-100 p-4">
					<div class="min-w-0 flex-1">
						<PeriodFilter
							from={period.from}
							to={period.to}
							onchange={(range) => (period = range)}
						/>
					</div>
					<a href={`/groups/${groupId}/analise`} class="btn btn-sm flex-none">
						{t('stats.openAnalysis')}
					</a>
				</div>

				<Records records={stats.records} {stats} />

				<div class="card flex flex-col gap-4 bg-base-100 p-5">
					<div class="charthead">
						<div>
							<h3 class="font-semibold">
								{metric === 'win_rate'
									? t('stats.evolution')
									: `${metric === 'goals' ? t('chart.metricGoals') : t('chart.metricAssists')} · ${t('chart.cumulative')}`}
							</h3>
							{#if metric === 'win_rate'}
								<p class="mt-1 text-xs text-base-content/65">{t('stats.evolutionHint')}</p>
							{/if}
						</div>
						<div class="metrics" role="group" aria-label={t('chart.metric')}>
							{#each [{ id: 'win_rate', label: t('chart.metricRate'), on: true }, { id: 'goals', label: t('chart.metricGoals'), on: group.track_scorers }, { id: 'assists', label: t('chart.metricAssists'), on: group.track_scorers && group.track_assists }] as option (option.id)}
								{#if option.on}
									<button
										type="button"
										class="mchip"
										class:sel={metric === option.id}
										aria-pressed={metric === option.id}
										onclick={() => (metric = /** @type {any} */ (option.id))}
									>
										{option.label}
									</button>
								{/if}
							{/each}
						</div>
					</div>
					<EvolutionChart {evolution} {metric} />
				</div>

				{#if timeline}
					<TimelineCharts {timeline} />
				{/if}

				{#if pairs}
					<PairLeaderboard
						board={pairs}
						{minDays}
						onMinDays={(value) => (minDays = value)}
						{playerHref}
					/>
				{/if}

				{#if network && group.track_scorers && group.track_assists}
					<AssistNetwork {network} {playerHref} />
				{/if}
			</div>
		{:else if tab === 'settings'}
			<GroupSettings {group} onchange={onGroupChange} />
		{/if}
	</div>
{/if}

<style>
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
	.charthead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.metrics {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.mchip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.mchip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.periodbar {
		display: flex;
		flex-direction: row;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	@media (max-width: 640px) {
		.periodbar :global(.btn) {
			width: 100%;
		}
	}
</style>
