<script>
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ value: number, onchange: (value: number) => void }} */
	let { value, onchange } = $props();
</script>

<label class="mindays">
	<span>{t('player.minDays')}</span>
	<input
		class="input input-sm"
		type="number"
		min="1"
		max="50"
		{value}
		onchange={(e) => onchange(Number(e.currentTarget.value) || 1)}
	/>
</label>

<style>
	.mindays {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		font-size: 0.76rem;
		white-space: nowrap;
		color: var(--ink-muted);
	}
	.mindays input {
		width: 4.2rem;
	}
</style>
