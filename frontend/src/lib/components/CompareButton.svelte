<script>
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ label: string, onclick: () => void }} */
	let { label, onclick } = $props();
</script>

<button type="button" class="btn btn-ghost btn-xs" aria-label={label} {onclick}>
	{t('compare.view')}
</button>
