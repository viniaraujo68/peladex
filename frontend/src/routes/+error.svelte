<script>
	import { page } from '$app/stores';
	import { t } from '$lib/i18n.svelte.js';
	import BrandMark from '$lib/components/BrandMark.svelte';

	const notFound = $derived($page.status === 404);
	const title = $derived(notFound ? t('error.notFoundTitle') : t('error.title'));
	const body = $derived(notFound ? t('error.notFoundBody') : t('error.body'));
</script>

<svelte:head>
	<title>{notFound ? t('title.notFound') : t('title.error')}</title>
</svelte:head>

<div class="errbox card mx-auto mt-[8vh] max-w-[520px] items-center gap-3 bg-base-100 px-6 py-10">
	<span class="glyph"><BrandMark /></span>
	<span class="badge badge-soft">{t('error.http', { status: $page.status })}</span>
	<h1 class="text-2xl font-semibold tracking-tight">{title}</h1>
	<p class="text-base-content/80">{body}</p>
	{#if $page.error?.message && !notFound}
		<p class="detail text-base-content/65">{$page.error.message}</p>
	{/if}
	<a href="/" class="btn">{t('error.home')}</a>
</div>

<style>
	.errbox {
		text-align: center;
	}
	.glyph {
		display: grid;
		place-items: center;
		width: 56px;
		height: 56px;
		border-radius: var(--radius-box);
		background-color: var(--color-primary);
		color: var(--color-primary-content);
		font-size: 2.45rem;
	}
	.detail {
		font-size: 0.82rem;
		overflow-wrap: anywhere;
	}
</style>
