<script>
	/** @type {{ side: 'a'|'b'|null }} */
	let { side } = $props();
</script>

{#if side}<span class="dot {side}" aria-hidden="true"></span>{/if}

<style>
	.dot {
		display: inline-block;
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 999px;
		background: var(--color-primary);
	}
	.dot.b {
		background: var(--color-warning);
	}
</style>
