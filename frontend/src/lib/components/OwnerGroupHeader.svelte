<script>
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ groupId: string, name: string, description?: string|null }} */
	let { groupId, name, description = null } = $props();
</script>

<div class="head flex items-start justify-between gap-3">
	<div>
		<a href="/" class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content">
			{t('group.back')}
		</a>
		<h1 class="text-2xl font-semibold tracking-tight">{name}</h1>
		{#if description}<p class="mt-1 text-base-content/80">{description}</p>{/if}
	</div>
	<div class="headbtns flex gap-2">
		<a href={`/groups/${groupId}/matchdays/import`} class="btn">{t('group.importText')}</a>
		<a href={`/groups/${groupId}/matchdays/new`} class="btn btn-primary">
			{t('group.newMatchday')}
		</a>
	</div>
</div>

<style>
	.head {
		margin-bottom: 20px;
	}
	@media (max-width: 640px) {
		.head {
			flex-direction: column;
			align-items: stretch;
			gap: 12px;
		}
		.headbtns :global(.btn) {
			flex: 1;
		}
	}
</style>
