<script>
	import { teamColor } from '$lib/teamColor.js';

	/** @type {{ name: string, color?: string, class?: string }} */
	let { name, color = '', class: className = 'size-[1.05em]' } = $props();

	const paint = $derived(teamColor(name, color));
</script>

<svg
	class="crest {className}"
	viewBox="0 0 24 24"
	role="img"
	aria-label={name}
	style="--crest-paint: {paint}"
>
	<path
		d="M12 2.4 4.6 5.1v6.3c0 4.5 3 8.4 7.4 9.9 4.4-1.5 7.4-5.4 7.4-9.9V5.1Z"
		fill="var(--crest-paint)"
	/>
	<path
		d="M12 2.4 4.6 5.1v6.3c0 4.5 3 8.4 7.4 9.9 4.4-1.5 7.4-5.4 7.4-9.9V5.1Z"
		fill="none"
		stroke="var(--crest-edge)"
		stroke-width="1.7"
	/>
	<path d="M12 2.4v18.9" stroke="var(--crest-edge)" stroke-width="1.1" fill="none" opacity="0.5" />
</svg>

<style>
	.crest {
		--crest-edge: color-mix(in oklch, var(--color-base-content) 62%, transparent);
		flex: none;
		display: inline-block;
		vertical-align: -0.15em;
	}
</style>
