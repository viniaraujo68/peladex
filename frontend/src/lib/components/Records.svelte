<script>
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';

	const tracking = getTracking();
	const GOAL_RECORDS = ['top_scorer', 'most_goals_matchday'];
	const ASSIST_RECORDS = ['top_assister', 'most_assists_matchday', 'best_duo'];

	/**
	 * @type {{
	 *   records: import('$lib/types.js').GroupRecord[],
	 *   stats: import('$lib/types.js').Stats
	 * }}
	 */
	let { records, stats } = $props();

	/** @param {string|null} d */
	function fmtDate(d) {
		return d ? new Date(d + 'T00:00:00').toLocaleDateString(localeTag()) : '';
	}

	/** @param {import('$lib/types.js').GroupRecord} record */
	function valueText(record) {
		if (record.value === null) return '—';
		const count = record.value;
		if (['top_scorer', 'most_goals_matchday', 'best_duo'].includes(record.code)) {
			return t('records.goals', { count });
		}
		if (['top_assister', 'most_assists_matchday'].includes(record.code)) {
			return t('records.assists', { count });
		}
		if (record.code === 'most_titles') return t('records.days', { count });
		if (record.code === 'most_presence') return t('records.presenceDays', { count });
		if (record.code === 'most_mvp') return t('records.mvps', { count });
		if (record.code === 'biggest_rout') return t('records.margin', { count });
		return String(count);
	}

	const visible = $derived(
		records.filter((r) => {
			if (GOAL_RECORDS.includes(r.code)) return tracking.trackScorers;
			if (ASSIST_RECORDS.includes(r.code)) return tracking.trackScorers && tracking.trackAssists;
			return true;
		})
	);

	/** @param {import('$lib/types.js').GroupRecord} record */
	function subtitle(record) {
		const parts = [];
		if (record.player_name) parts.push(record.player_name);
		if (record.detail) parts.push(record.detail);
		if (record.matchday_date) parts.push(fmtDate(record.matchday_date));
		return parts.join(' · ');
	}
</script>

<div class="records">
	<div class="card flex flex-col gap-1 bg-base-100 p-4">
		<span class="rec-label">{t('records.totalMatchdays')}</span>
		<span class="rec-value">{stats.total_matchdays}</span>
	</div>
	<div class="card flex flex-col gap-1 bg-base-100 p-4">
		<span class="rec-label">{t('records.totalMatches')}</span>
		<span class="rec-value">{stats.total_matches}</span>
	</div>
	{#if tracking.trackScorers}
		<div class="card flex flex-col gap-1 bg-base-100 p-4">
			<span class="rec-label">{t('records.totalGoals')}</span>
			<span class="rec-value">{stats.total_goals}</span>
		</div>
	{/if}
	{#if tracking.trackScorers && tracking.trackAssists}
		<div class="card flex flex-col gap-1 bg-base-100 p-4">
			<span class="rec-label">{t('records.totalAssists')}</span>
			<span class="rec-value">{stats.total_assists}</span>
		</div>
	{/if}
	{#each visible as record (record.code)}
		<div class="card flex flex-col gap-1 bg-base-100 p-4">
			<span class="rec-label">{t(`records.${record.code}`)}</span>
			<span class="rec-value" class:muted={record.value === null}>{valueText(record)}</span>
			{#if record.value !== null && subtitle(record)}
				<span class="rec-sub">{subtitle(record)}</span>
			{/if}
		</div>
	{/each}
</div>

<style>
	.records {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 14px;
	}
	.rec-label {
		font-size: 0.6875rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.rec-value {
		font-size: 1.4rem;
		font-weight: 500;
		letter-spacing: -0.01em;
	}
	.rec-value.muted {
		color: var(--ink-muted);
	}
	.rec-sub {
		font-size: 0.76rem;
		color: var(--ink-muted);
		overflow-wrap: anywhere;
	}
</style>
