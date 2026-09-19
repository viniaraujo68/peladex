<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n.svelte.js';
	import PlayerProfile from '$lib/components/PlayerProfile.svelte';

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

	const tokenQuery = $derived(token ? `t=${encodeURIComponent(token)}` : '');

	/** @param {number} playerId */
	const playerHref = (playerId) =>
		`/g/${slug}/players/${playerId}${tokenQuery ? `?${tokenQuery}` : ''}`;

	const backHref = $derived(`/g/${slug}${tokenQuery ? `?${tokenQuery}` : ''}`);

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
	<div class="head mb-5">
		<a href={backHref} class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content">
			{t('player.backToGroup')}
		</a>
		<h1 class="text-2xl font-semibold tracking-tight">{detail.name}</h1>
		<p class="mt-1 text-base-content/80">{group.name}</p>
	</div>

	<PlayerProfile
		{detail}
		evolution={group.evolution}
		minDays={data.minDays}
		onMinDays={setMinDays}
		{playerHref}
	/>
{/if}
