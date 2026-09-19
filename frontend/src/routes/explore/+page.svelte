<script>
	import { get } from '$lib/http.js';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ data: { groups: import('$lib/types.js').PublicGroupSummary[], status: number } }} */
	let { data } = $props();

	let query = $state('');
	// svelte-ignore state_referenced_locally
	let results = $state(/** @type {import('$lib/types.js').PublicGroupSummary[]} */ (data.groups));
	let searching = $state(false);

	$effect(() => {
		const term = query.trim();
		const timer = setTimeout(async () => {
			searching = true;
			try {
				results = await get(`/public?q=${encodeURIComponent(term)}`);
			} catch {
				results = [];
			} finally {
				searching = false;
			}
		}, 250);
		return () => clearTimeout(timer);
	});
</script>

<svelte:head>
	<title>{t('title.explore')}</title>
	<meta name="description" content={t('explore.subtitle')} />
</svelte:head>

<div class="head mb-6">
	<h1 class="text-2xl font-semibold tracking-tight">{t('explore.title')}</h1>
	<p class="mt-1 text-base-content/80">{t('explore.subtitle')}</p>
</div>

<label class="input mb-5 w-full max-w-[360px]">
	<Icon name="search" class="size-4 opacity-55" />
	<input placeholder={t('explore.searchPlaceholder')} bind:value={query} />
</label>

{#if searching && results.length === 0}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
		{t('explore.searching')}
	</div>
{:else if results.length === 0}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
		{query.trim() ? t('explore.noResults', { query }) : t('explore.empty')}
	</div>
{:else}
	<div class="groups grid gap-4">
		{#each results as g (g.slug)}
			<GroupCard group={g} href={`/g/${g.slug}`} />
		{/each}
	</div>
{/if}

<style>
	.groups {
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	}
</style>
