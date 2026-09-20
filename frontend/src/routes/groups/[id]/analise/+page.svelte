<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { get, post, errorMessage } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import ComboExplorer from '$lib/components/ComboExplorer.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let players = $state(/** @type {import('$lib/types.js').Player[]} */ ([]));
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) load();
	});

	async function load() {
		loading = true;
		try {
			[group, players] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players`)
			]);
		} catch (e) {
			error = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/** @param {any} body */
	const run = (body) => post(`/groups/${groupId}/combo`, body);
</script>

<svelte:head><title>{t('analysis.title')} · Peladex</title></svelte:head>

<div class="head mb-5">
	<a
		href={`/groups/${groupId}?tab=stats`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('day.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">{t('analysis.title')}</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

{#if loading}
	<div class="flex flex-col gap-4" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<Skeleton class="h-[120px]" />
		<Skeleton class="h-[220px]" />
	</div>
{:else if error}
	<div class="alert alert-soft alert-error">{error}</div>
{:else}
	<ComboExplorer players={players.map((p) => ({ id: p.id, name: p.name }))} {run} />
{/if}
