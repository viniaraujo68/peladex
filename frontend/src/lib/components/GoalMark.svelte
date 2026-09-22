<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   player: string,
	 *   assist?: string|null,
	 *   ownGoal?: boolean,
	 *   showAssist?: boolean,
	 *   mirror?: boolean,
	 *   size?: string
	 * }}
	 */
	let {
		player,
		assist = null,
		ownGoal = false,
		showAssist = true,
		mirror = false,
		size = 'size-[0.95em]'
	} = $props();
</script>

<span class="gm" class:own={ownGoal} class:mirror>
	<Icon
		name="ball"
		class="{size} gm-ball"
		label={ownGoal ? t('day.ownGoal') : t('records.totalGoals')}
	/>
	<span class="gm-text">
		<span class="gm-name">{player}</span>
		{#if showAssist && assist && !ownGoal}
			<span class="gm-assist" title={t('day.assist')}>({assist})</span>
		{/if}
	</span>
</span>

<style>
	.gm {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		white-space: nowrap;
	}
	.gm.mirror {
		flex-direction: row-reverse;
	}
	.gm :global(.gm-ball) {
		flex: none;
		color: var(--color-base-content);
	}
	.gm.own :global(.gm-ball) {
		color: var(--goal-own, color-mix(in oklab, var(--color-error) 92%, var(--color-base-content)));
	}
	.gm-text {
		display: inline-flex;
		align-items: baseline;
		gap: 4px;
	}
	.gm.mirror .gm-text {
		flex-direction: row-reverse;
	}
	.gm-name {
		font-weight: 600;
	}
	.gm.own .gm-name {
		color: var(--goal-own, color-mix(in oklab, var(--color-error) 92%, var(--color-base-content)));
	}
	.gm-assist {
		color: color-mix(in oklch, var(--color-base-content) 68%, transparent);
	}
</style>
