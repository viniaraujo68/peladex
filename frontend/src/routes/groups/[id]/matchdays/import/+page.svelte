<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get, errorMessage } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import ImportPanel from '$lib/components/ImportPanel.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let players = $state(/** @type {import('$lib/types.js').Player[]} */ ([]));
	let error = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) load();
	});

	async function load() {
		try {
			[group, players] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players`)
			]);
		} catch (e) {
			error = errorMessage(e);
		}
	}

	/** @param {{ created: number, replaced: number }} _result */
	function onimported(_result) {
		goto(`/groups/${groupId}`);
	}
</script>

<svelte:head><title>{t('title.importMatchday')}</title></svelte:head>

<div class="head mb-5">
	<a
		href={`/groups/${groupId}`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('day.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">{t('import.title')}</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

{#if error}
	<div class="alert alert-soft alert-error">{error}</div>
{:else}
	<ImportPanel
		{groupId}
		players={players.filter((p) => p.active).map((p) => ({ id: p.id, name: p.name }))}
		defaultVenue={group?.default_venue_name ?? null}
		trackScorers={group?.track_scorers ?? true}
		trackAssists={group?.track_assists ?? false}
		{onimported}
	/>
{/if}
