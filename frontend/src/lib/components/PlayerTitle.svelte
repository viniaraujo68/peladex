<script>
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ name: string, playersHref: string }} */
	let { name, playersHref } = $props();
</script>

<div class="title">
	<a href={playersHref} class="crumb link-hover">{t('tab.players')} ›</a>
	<h2 class="text-2xl font-semibold tracking-tight">{name}</h2>
</div>

<style>
	.title {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 16px;
	}
	.crumb {
		align-self: flex-start;
		font-size: 0.82rem;
		color: var(--ink-muted);
	}
</style>
