<script>
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { get, errorMessage, errorStatus } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import { setGroupTracking } from '$lib/tracking.svelte.js';
	import DayTypeFilter from '$lib/components/DayTypeFilter.svelte';
	import OwnerGroupHeader from '$lib/components/OwnerGroupHeader.svelte';
	import PlayerProfile from '$lib/components/PlayerProfile.svelte';
	import PlayerTitle from '$lib/components/PlayerTitle.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { ownerTabs } from '$lib/groupTabs.js';
	import { dayTypeParam, dayTypeQuery, withDayType, setDayTypeContext } from '$lib/dayType.js';
	import { replaceParams } from '$lib/groupView.svelte.js';

	const groupId = $derived(/** @type {string} */ ($page.params.id));
	const playerId = $derived(/** @type {string} */ ($page.params.playerId));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let detail = $state(/** @type {import('$lib/types.js').PlayerDetail|null} */ (null));
	let evolution = $state(/** @type {import('$lib/types.js').Evolution|null} */ (null));
	let minDays = $state(3);
	let loading = $state(true);

	setGroupTracking(() => group);
	setDayTypeContext(() => detail?.days);
	let error = $state('');

	const dayType = $derived(dayTypeParam($page.url.searchParams));

	/** @param {number} id */
	const playerHref = (id) => withDayType(`/groups/${groupId}/players/${id}`, dayType);

	/** @param {string} tab */
	const tabHref = (tab) => withDayType(`/groups/${groupId}?tab=${tab}`, dayType);

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		const days = minDays;
		const query = dayTypeQuery(dayType);
		const group_ = groupId;
		const player_ = playerId;
		if (group_ && player_ && auth.user) load(days, query);
	});

	/** @param {number} days @param {string} query */
	async function load(days, query) {
		loading = untrack(() => detail === null);
		error = '';
		try {
			[group, detail, evolution] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players/${playerId}/detail?${[`min_days=${days}`, query].filter(Boolean).join('&')}`),
				get(`/groups/${groupId}/evolution${query ? `?${query}` : ''}`)
			]);
		} catch (e) {
			error = errorStatus(e) === 403 ? t('group.accessDenied') : errorMessage(e);
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>{detail ? t('title.player', { name: detail.name }) : t('title.home')}</title>
</svelte:head>

{#if group}
	<OwnerGroupHeader {groupId} name={group.name} description={group.description} />
	<TabBar
		tabs={ownerTabs()}
		active="players"
		onChange={(tab) => goto(tabHref(tab))}
		label={t('tab.sections')}
		controls="group-panel"
	/>
{/if}

<div id="group-panel" role="tabpanel" aria-labelledby="tab-players">
	{#if loading}
		<div class="flex flex-col gap-4" role="status">
			<span class="sr-only">{t('common.loading')}</span>
			<div class="grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))">
				{#each [0, 1, 2, 3] as i (i)}<Skeleton class="h-[86px]" />{/each}
			</div>
			<Skeleton class="h-[300px]" />
		</div>
	{:else if error}
		<div class="alert alert-soft alert-error">{error}</div>
	{:else if detail && evolution}
		<PlayerTitle name={detail.name} playersHref={tabHref('players')} />
		<div class="mb-4">
			<DayTypeFilter days={detail.days} onchange={(value) => replaceParams({ day_type: value })} />
		</div>
		{#key dayType}
			<PlayerProfile
				{detail}
				{evolution}
				{minDays}
				onMinDays={(value) => (minDays = value)}
				{playerHref}
			/>
		{/key}
	{/if}
</div>
