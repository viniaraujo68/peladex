<script>
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ rank: number|null, previous: number|null }} */
	let { rank, previous } = $props();

	const change = $derived(rank !== null && previous !== null ? previous - rank : null);
</script>

{#if rank !== null}
	{#if previous === null}
		<span class="move new" title={t('move.newHint')}>{t('move.new')}</span>
	{:else if change && change > 0}
		<span class="move up" title={t('move.upHint', { count: change })}>▲{change}</span>
	{:else if change && change < 0}
		<span class="move down" title={t('move.downHint', { count: -change })}>▼{-change}</span>
	{/if}
{/if}

<style>
	.move {
		display: inline-block;
		margin-left: 5px;
		font-size: 0.68rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		vertical-align: 0.08em;
	}
	.up {
		color: var(--color-success);
	}
	.down {
		color: var(--color-error);
	}
	.new {
		padding: 0 5px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
</style>
