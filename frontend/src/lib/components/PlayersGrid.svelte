<script>
	import { formatRate } from '$lib/format.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { getTracking } from '$lib/tracking.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { ranking, playerHref } = $props();

	const tracking = getTracking();

	let query = $state('');
	let order = $state(/** @type {'rate'|'name'|'goals'|'days'} */ ('rate'));

	const orders = $derived([
		{ id: 'rate', label: t('ranking.winRate') },
		{ id: 'name', label: t('ranking.player') },
		...(tracking.trackScorers ? [{ id: 'goals', label: t('ranking.goals') }] : []),
		{ id: 'days', label: t('ranking.matchdays') }
	]);

	const filtered = $derived.by(() => {
		const term = query.trim().toLowerCase();
		const rows = term
			? ranking.filter((r) => r.name.toLowerCase().includes(term))
			: [...ranking];
		if (order === 'name') return rows.sort((a, b) => a.name.localeCompare(b.name, localeTag()));
		if (order === 'goals') return rows.sort((a, b) => b.goals - a.goals);
		if (order === 'days') return rows.sort((a, b) => b.matchdays - a.matchdays);
		return rows.sort((a, b) => b.win_rate - a.win_rate);
	});
</script>

{#if ranking.length === 0}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
		{t('ranking.empty')}
	</div>
{:else}
	<div class="wrap">
		<div class="bar">
			<label class="input search">
				<Icon name="search" class="size-4 opacity-55" />
				<input placeholder={t('players.search')} bind:value={query} />
			</label>
			<div class="orders" role="group" aria-label={t('players.sortBy')}>
				{#each orders as option (option.id)}
					<button
						type="button"
						class="ochip"
						class:sel={order === option.id}
						aria-pressed={order === option.id}
						onclick={() => (order = /** @type {any} */ (option.id))}
					>
						{option.label}
					</button>
				{/each}
			</div>
		</div>

		{#if filtered.length === 0}
			<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
				{t('home.noResults', { query })}
			</div>
		{:else}
			<div class="grid">
				{#each filtered as row (row.player_id)}
					<a class="pcard card bg-base-100 p-4" href={playerHref(row.player_id)}>
						<div class="ph">
							<span class="pname">{row.name}</span>
							{#if row.mvp_count > 0}
								<span class="mvp" title={t('ranking.mvp')}>
									<Icon name="star" class="size-3" />{row.mvp_count}
								</span>
							{/if}
						</div>
						<div class="prate">{formatRate(row.win_rate)}</div>
						<div class="pmeta">
							{t('players.meta', {
								days: row.matchdays,
								matches: row.matches,
								presence: formatRate(row.presence)
							})}
						</div>
						<div class="pchips">
							{#if tracking.trackScorers}
								<span class="chip">
									<Icon name="ball" class="size-3" />{row.goals}
								</span>
							{/if}
							{#if tracking.trackScorers && tracking.trackAssists}
								<span class="chip">
									<Icon name="boot" class="size-3" />{row.assists}
								</span>
							{/if}
							<span class="chip">
								<Icon name="trophy" class="size-3" />{row.titles}
							</span>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.search {
		max-width: 300px;
		flex: 1 1 200px;
	}
	.orders {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.ochip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.ochip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
		gap: 12px;
	}
	.pcard {
		display: flex;
		flex-direction: column;
		gap: 4px;
		transition:
			transform 0.12s ease,
			border-color 0.15s ease;
	}
	.pcard:hover {
		transform: translateY(-2px);
		border-color: color-mix(in oklch, var(--color-primary) 55%, transparent);
	}
	@media (prefers-reduced-motion: reduce) {
		.pcard:hover {
			transform: none;
		}
	}
	.ph {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 6px;
	}
	.pname {
		font-weight: 700;
		overflow-wrap: anywhere;
	}
	.mvp {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		flex: none;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--ink-primary);
	}
	.prate {
		font-size: 1.4rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
		color: var(--ink-primary);
	}
	.pmeta {
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
	.pchips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-top: 4px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 7px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		font-size: 0.72rem;
		font-variant-numeric: tabular-nums;
		color: color-mix(in oklch, var(--color-base-content) 78%, transparent);
	}
	@media (max-width: 560px) {
		.ochip {
			min-height: 40px;
		}
	}
</style>
