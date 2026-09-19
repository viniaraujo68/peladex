<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   group: { name: string, description?: string, matchday_count: number, player_count: number },
	 *   href: string,
	 *   visibility?: 'public'|'private'
	 * }}
	 */
	let { group, href, visibility = 'public' } = $props();
</script>

<a {href} class="gcard card flex flex-col gap-3 bg-base-100 p-5">
	<div class="flex items-center justify-between gap-3">
		<h3 class="font-semibold">{group.name}</h3>
		<span class="badge badge-soft {visibility === 'public' ? 'badge-primary' : ''}">
			{visibility === 'public' ? t('group.chipPublic') : t('group.chipPrivate')}
		</span>
	</div>
	{#if group.description}
		<p class="text-sm text-base-content/80">{group.description}</p>
	{/if}
	<div class="mt-auto flex flex-wrap items-center gap-2">
		<span class="badge badge-soft">
			<Icon name="calendar" />
			{t('group.matchdayCount', { count: group.matchday_count })}
		</span>
		<span class="badge badge-soft">
			<Icon name="players" />
			{t('group.playerCount', { count: group.player_count })}
		</span>
	</div>
</a>

<style>
	.gcard {
		transition:
			transform 0.12s ease,
			border-color 0.15s ease;
	}
	.gcard:hover {
		transform: translateY(-3px);
		border-color: color-mix(in oklch, var(--color-primary) 55%, transparent);
	}
	@media (prefers-reduced-motion: reduce) {
		.gcard:hover {
			transform: none;
		}
	}
</style>
