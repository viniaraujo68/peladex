<script>
	import { formatShortDate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ form: import('$lib/types.js').FormEntry[] }} */
	let { form } = $props();

	/** @param {import('$lib/types.js').FormEntry} entry */
	function tone(entry) {
		if (entry.champion) return 'first';
		if (entry.position === entry.teams) return 'last';
		return 'middle';
	}

	/** @param {import('$lib/types.js').FormEntry} entry */
	function describe(entry) {
		const place = entry.champion
			? t('form.champion')
			: t('player.positionOf', { position: entry.position, teams: entry.teams });
		return `${formatShortDate(entry.date)}: ${place}`;
	}

	const label = $derived(form.map(describe).join(' · '));
</script>

{#if form.length === 0}
	<span class="none">—</span>
{:else}
	<span class="dots" role="img" aria-label={label} title={label}>
		{#each form as entry, index (index)}
			<span class="dot" data-tone={tone(entry)}>{entry.champion ? '' : entry.position}</span>
		{/each}
	</span>
{/if}

<style>
	.dots {
		display: inline-flex;
		gap: 3px;
		vertical-align: middle;
	}
	.dot {
		display: inline-grid;
		place-items: center;
		width: 15px;
		height: 15px;
		border-radius: 999px;
		font-size: 0.55rem;
		font-weight: 700;
		line-height: 1;
		color: var(--color-base-100);
	}
	.dot[data-tone='first'] {
		background: var(--color-success);
	}
	.dot[data-tone='middle'] {
		background: color-mix(in oklch, var(--color-base-content) 35%, transparent);
	}
	.dot[data-tone='last'] {
		background: var(--color-error);
	}
	.none {
		color: var(--ink-muted);
	}
</style>
