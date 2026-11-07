<script>
	import { publicErrorMessage } from '$lib/publicApi.js';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n.svelte.js';
	import { setGroupTracking } from '$lib/tracking.svelte.js';
	import DayTypeFilter from '$lib/components/DayTypeFilter.svelte';
	import PlayerProfile from '$lib/components/PlayerProfile.svelte';
	import PlayerTitle from '$lib/components/PlayerTitle.svelte';
	import PublicGroupHeader from '$lib/components/PublicGroupHeader.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { publicTabs } from '$lib/groupTabs.js';
	import { dayTypeParam, dayTypeQuery, setDayTypeContext } from '$lib/dayType.js';
	import { replaceParams } from '$lib/groupView.svelte.js';

	/**
	 * @type {{ data: {
	 *   detail: import('$lib/types.js').PlayerDetail|null,
	 *   group: import('$lib/types.js').PublicGroup|null,
	 *   status: number,
	 *   minDays: number
	 * } }}
	 */
	let { data } = $props();

	const detail = $derived(data.detail);
	const group = $derived(data.group);

	setGroupTracking(() => group);
	setDayTypeContext(() => detail?.days);
	const token = $derived($page.url.searchParams.get('t'));
	const slug = $derived(/** @type {string} */ ($page.params.slug));

	const error = $derived(publicErrorMessage(data.status));

	const tokenQuery = $derived(token ? `t=${encodeURIComponent(token)}` : '');
	const dayType = $derived(dayTypeParam($page.url.searchParams));
	const filterQuery = $derived([tokenQuery, dayTypeQuery(dayType)].filter(Boolean).join('&'));

	/** @param {number} playerId */
	const playerHref = (playerId) =>
		`/g/${slug}/players/${playerId}${filterQuery ? `?${filterQuery}` : ''}`;

	/** @param {string} tab */
	const tabHref = (tab) => `/g/${slug}?${[`tab=${tab}`, filterQuery].filter(Boolean).join('&')}`;

	/** @param {number} value */
	function setMinDays(value) {
		const url = new URL($page.url);
		url.searchParams.set('min', String(value));
		goto(url, { keepFocus: true, noScroll: true });
	}

	const title = $derived(detail ? t('title.player', { name: detail.name }) : t('title.home'));
</script>

<svelte:head>
	<title>{title}</title>
	{#if detail && group}
		<meta
			name="description"
			content={`${detail.name} · ${group.name} · ${t('public.metaTagline')}`}
		/>
		<meta property="og:type" content="profile" />
		<meta property="og:site_name" content="Peladex" />
		<meta property="og:title" content={title} />
		<meta property="og:url" content={$page.url.origin + $page.url.pathname} />
	{/if}
	{#if token}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

{#if error}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">{error}</div>
{:else if detail && group}
	<PublicGroupHeader name={group.name} description={group.description} />
	<TabBar
		tabs={publicTabs()}
		active="players"
		onChange={(tab) => goto(tabHref(tab))}
		label={t('tab.sections')}
		controls="public-panel"
		idPrefix="ptab"
		center
	/>
	<div id="public-panel" role="tabpanel" aria-labelledby="ptab-players">
		<PlayerTitle name={detail.name} playersHref={tabHref('players')} />
		<div class="mb-4">
			<DayTypeFilter days={detail.days} onchange={(value) => replaceParams({ day_type: value })} />
		</div>
		{#key dayType}
			<PlayerProfile
				{detail}
				evolution={group.evolution}
				minDays={data.minDays}
				onMinDays={setMinDays}
				{playerHref}
			/>
		{/key}
	</div>
{/if}
