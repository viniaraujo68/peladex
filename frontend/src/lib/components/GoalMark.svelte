<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   player: string,
	 *   assist?: string|null,
	 *   ownGoal?: boolean,
	 *   showAssist?: boolean,
	 *   size?: string
	 * }}
	 */
	let { player, assist = null, ownGoal = false, showAssist = true, size = 'size-[0.95em]' } =
		$props();
</script>

<span class="gm" class:own={ownGoal}>
	<Icon
		name="ball"
		class="{size} gm-ball"
		label={ownGoal ? t('day.ownGoal') : t('records.totalGoals')}
	/>
	<span class="gm-name">{player}</span>
	{#if showAssist && assist && !ownGoal}
		<Icon name="boot" class="{size} gm-boot" label={t('day.assist')} />
		<span class="gm-assist">{assist}</span>
	{/if}
</span>

<style>
	.gm {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		white-space: nowrap;
	}
	.gm :global(.gm-ball) {
		flex: none;
		color: var(--color-base-content);
	}
	.gm.own :global(.gm-ball) {
		color: var(--goal-own, color-mix(in oklab, var(--color-error) 92%, var(--color-base-content)));
	}
	.gm-name {
		font-weight: 600;
	}
	.gm.own .gm-name {
		color: var(--goal-own, color-mix(in oklab, var(--color-error) 92%, var(--color-base-content)));
	}
	.gm :global(.gm-boot) {
		flex: none;
		margin-left: 4px;
		color: color-mix(in oklch, var(--color-base-content) 52%, transparent);
	}
	.gm-assist {
		color: color-mix(in oklch, var(--color-base-content) 68%, transparent);
	}
</style>
