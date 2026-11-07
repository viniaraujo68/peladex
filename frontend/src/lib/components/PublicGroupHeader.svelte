<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/** @type {{ name: string, description?: string|null }} */
	let { name, description = null } = $props();
</script>

<div class="head">
	<span class="badge badge-soft badge-primary">
		<Icon name="ball" />
		{t('public.badge')}
	</span>
	<h1 class="text-[2rem] font-semibold tracking-tight">{name}</h1>
	{#if description}<p class="text-base-content/80">{description}</p>{/if}
</div>

<style>
	.head {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		text-align: center;
		margin-bottom: 24px;
	}
</style>
