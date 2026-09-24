<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/** @type {{ backLabel: string, query: string, onBack: () => void }} */
	let { backLabel, query = $bindable(), onBack } = $props();
</script>

<div class="bar">
	<button type="button" class="btn btn-sm btn-ghost" onclick={onBack}>{backLabel}</button>
	<label class="input search">
		<Icon name="search" class="size-4 opacity-55" />
		<input placeholder={t('players.search')} bind:value={query} />
	</label>
</div>

<style>
	.bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.search {
		max-width: 300px;
		flex: 1 1 200px;
	}
</style>
