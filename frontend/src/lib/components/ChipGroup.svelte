<script>
	/**
	 * @type {{
	 *   options: { id: string, label: string }[],
	 *   value: string,
	 *   label: string,
	 *   caption?: string,
	 *   onchange: (id: string) => void
	 * }}
	 */
	let { options, value, label, caption = '', onchange } = $props();
</script>

<div class="group">
	{#if caption}<span class="caption">{caption}</span>{/if}
	<div class="chips" role="group" aria-label={label}>
		{#each options as option (option.id)}
			<button
				type="button"
				class="chip"
				class:sel={value === option.id}
				aria-pressed={value === option.id}
				onclick={() => option.id !== value && onchange(option.id)}
			>
				{option.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.group {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 8px;
	}
	.caption {
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.chip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.chip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	@media (max-width: 560px) {
		.chip {
			min-height: 40px;
		}
	}
</style>
