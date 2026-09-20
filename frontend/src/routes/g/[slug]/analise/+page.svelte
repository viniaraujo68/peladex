<script>
	import { page } from '$app/stores';
	import { post } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import ComboExplorer from '$lib/components/ComboExplorer.svelte';

	/** @type {{ data: { group: import('$lib/types.js').PublicGroup|null, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	const slug = $derived(/** @type {string} */ ($page.params.slug));
	const token = $derived($page.url.searchParams.get('t'));
	const tokenQuery = $derived(token ? `?t=${encodeURIComponent(token)}` : '');

	const error = $derived(
		data.status === 200
			? ''
			: data.status === 403
				? t('public.errorPrivate')
				: t('error.body')
	);

	const players = $derived(
		(group?.stats.ranking ?? []).map((r) => ({ id: r.player_id, name: r.name }))
	);

	/** @param {any} body */
	const run = (body) => post(`/public/${encodeURIComponent(slug)}/combo${tokenQuery}`, body);
</script>

<svelte:head>
	<title>{t('analysis.title')} · Peladex</title>
	{#if token}<meta name="robots" content="noindex" />{/if}
</svelte:head>

<div class="head mb-5">
	<a
		href={`/g/${slug}${tokenQuery}`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('player.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">{t('analysis.title')}</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

{#if error}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">{error}</div>
{:else if group}
	<ComboExplorer {players} {run} />
{/if}
