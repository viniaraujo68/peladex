<script>
	import { SegmentedControl } from '@viniaraujo68/plinth/components';
	import { dayTypeOptions, hasBothDayTypes } from '$lib/dayType.js';
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   days: import('$lib/types.js').Days,
	 *   onchange: (dayType: import('$lib/types.js').DayType) => void
	 * }}
	 */
	let { days, onchange } = $props();

	const options = $derived(dayTypeOptions());
</script>

{#if hasBothDayTypes(days)}
	<div class="card flex flex-col gap-2 bg-base-100 p-4">
		<SegmentedControl
			{options}
			value={days.day_type}
			label={t('dayType.label')}
			caption={t('dayType.caption')}
			onchange={(id) => onchange(/** @type {import('$lib/types.js').DayType} */ (id))}
		/>
		<p class="hint">
			{t(`dayType.hint.${days.day_type}`, {
				count: days.day_type === 'single' ? days.rotation_matchdays : days.single_game_matchdays,
				rotation: days.rotation_matchdays,
				single: days.single_game_matchdays
			})}
		</p>
	</div>
{/if}

<style>
	.hint {
		font-size: 0.78rem;
		color: var(--ink-muted);
	}
</style>
