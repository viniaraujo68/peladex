<script>
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { get, errorMessage, errorStatus } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import PlayerProfile from '$lib/components/PlayerProfile.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));
	const playerId = $derived(/** @type {string} */ ($page.params.playerId));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let detail = $state(/** @type {import('$lib/types.js').PlayerDetail|null} */ (null));
	let evolution = $state(/** @type {import('$lib/types.js').Evolution|null} */ (null));
	let minDays = $state(3);
	let loading = $state(true);
	let error = $state('');

	/** @param {number} id */
	const playerHref = (id) => `/groups/${groupId}/players/${id}`;

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		const days = minDays;
		const group_ = groupId;
		const player_ = playerId;
		if (group_ && player_ && auth.user) load(days);
	});

	/** @param {number} days */
	async function load(days) {
		loading = untrack(() => detail === null);
		error = '';
		try {
			[group, detail, evolution] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players/${playerId}/detail?min_days=${days}`),
				get(`/groups/${groupId}/evolution`)
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

<div class="head mb-5">
	<a
		href={`/groups/${groupId}?tab=ranking`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('player.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">{detail?.name ?? ''}</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

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
	<PlayerProfile
		{detail}
		{evolution}
		{minDays}
		onMinDays={(value) => (minDays = value)}
		{playerHref}
	/>
{/if}
