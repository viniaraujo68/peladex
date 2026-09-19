<script>
	import { Combobox } from '@viniaraujo68/plinth/components';
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';
	import MatchdayCard from './MatchdayCard.svelte';

	/**
	 * @type {{
	 *   matchdays: import('$lib/types.js').Matchday[],
	 *   editable?: boolean,
	 *   showMismatch?: boolean,
	 *   newHref?: string,
	 *   importHref?: string,
	 *   playerHref?: (playerId: number) => string,
	 *   onEdit?: (m: import('$lib/types.js').Matchday) => void,
	 *   onDelete?: (m: import('$lib/types.js').Matchday) => void
	 * }}
	 */
	let {
		matchdays,
		editable = false,
		showMismatch = true,
		newHref = '',
		importHref = '',
		playerHref,
		onEdit,
		onDelete
	} = $props();

	let venueFilter = $state('');
	let dateFrom = $state('');
	let dateTo = $state('');
	/** @type {Set<number>} */
	let selectedPlayers = $state(new Set());
	let filtersOpen = $state(false);

	const venues = $derived.by(() => {
		/** @type {Map<number, string>} */
		const map = new Map();
		for (const m of matchdays) if (m.venue_id) map.set(m.venue_id, m.venue_name ?? '');
		return [...map]
			.map(([id, name]) => ({ id, name }))
			.sort((a, b) => a.name.localeCompare(b.name));
	});

	/** @type {import('@viniaraujo68/plinth/components').SelectOption[]} */
	const venueOptions = $derived([
		{ value: '', label: t('common.all') },
		...venues.map((v) => ({ value: String(v.id), label: v.name }))
	]);

	const players = $derived.by(() => {
		/** @type {Map<number, string>} */
		const map = new Map();
		for (const m of matchdays) {
			for (const s of m.standings) {
				for (const member of s.members) map.set(member.player_id, member.name);
			}
		}
		return [...map]
			.map(([id, name]) => ({ id, name }))
			.sort((a, b) => a.name.localeCompare(b.name));
	});

	const filtered = $derived(
		matchdays.filter((m) => {
			if (venueFilter && m.venue_id !== Number(venueFilter)) return false;
			if (dateFrom && m.date < dateFrom) return false;
			if (dateTo && m.date > dateTo) return false;
			if (selectedPlayers.size) {
				const present = new Set(
					m.standings.flatMap((s) => s.members.map((member) => member.player_id))
				);
				for (const pid of selectedPlayers) if (!present.has(pid)) return false;
			}
			return true;
		})
	);

	const activeFilterCount = $derived(
		(venueFilter !== '' ? 1 : 0) +
			(dateFrom !== '' ? 1 : 0) +
			(dateTo !== '' ? 1 : 0) +
			selectedPlayers.size
	);

	const PAGE = 15;
	let shown = $state(PAGE);

	$effect(() => {
		venueFilter;
		dateFrom;
		dateTo;
		selectedPlayers;
		shown = PAGE;
	});

	const paged = $derived(filtered.slice(0, shown));

	/** @param {number} id */
	function togglePlayer(id) {
		const next = new Set(selectedPlayers);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedPlayers = next;
	}

	function clearFilters() {
		venueFilter = '';
		dateFrom = '';
		dateTo = '';
		selectedPlayers = new Set();
	}
</script>

{#if matchdays.length === 0}
	<div class="card items-center gap-4 bg-base-100 px-5 py-12 text-center">
		<p class="text-base-content/65">{t('day.noMatches')}</p>
		{#if newHref}
			<div class="flex flex-wrap justify-center gap-2">
				<a href={newHref} class="btn btn-primary">{t('group.newMatchday')}</a>
				{#if importHref}
					<a href={importHref} class="btn">{t('group.importText')}</a>
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<div class="list">
		<div class="card filters bg-base-100 p-4">
			<button
				type="button"
				class="fsummary"
				aria-expanded={filtersOpen}
				aria-controls="matchday-filters"
				onclick={() => (filtersOpen = !filtersOpen)}
			>
				<span class="fs-label">{t('filters.title')}</span>
				{#if activeFilterCount > 0}
					<span class="badge badge-soft badge-primary flex-none">{activeFilterCount}</span>
				{/if}
				<span class="fs-caret" class:open={filtersOpen}><Icon name="chevron" /></span>
			</button>

			<div class="fbody" id="matchday-filters" class:open={filtersOpen}>
				<div class="ftop">
					{#if venues.length > 1}
						<div class="frow">
							<label class="flabel" id="vf-label" for="vf">{t('day.venue')}</label>
							<Combobox
								id="vf"
								bind:value={() => venueFilter, (value) => (venueFilter = value ?? '')}
								options={venueOptions}
								aria-labelledby="vf-label"
								placeholder={t('day.venue')}
								clearable={venueFilter !== ''}
								clearLabel={t('common.remove')}
								class="w-full"
							/>
						</div>
					{/if}
					<div class="frow">
						<label class="flabel" for="df">{t('filters.from')}</label>
						<input
							id="df"
							class="input min-h-11 w-full"
							type="date"
							bind:value={dateFrom}
							max={dateTo || undefined}
						/>
					</div>
					<div class="frow">
						<label class="flabel" for="dt">{t('filters.to')}</label>
						<input
							id="dt"
							class="input min-h-11 w-full"
							type="date"
							bind:value={dateTo}
							min={dateFrom || undefined}
						/>
					</div>
				</div>

				{#if players.length}
					<div class="fplayers">
						<span class="flabel">{t('settings.players')}</span>
						<div class="pchips">
							{#each players as player (player.id)}
								<button
									type="button"
									class="badge badge-soft pchip"
									class:sel={selectedPlayers.has(player.id)}
									aria-pressed={selectedPlayers.has(player.id)}
									onclick={() => togglePlayer(player.id)}
								>
									{player.name}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<div class="fbottom">
					<span class="text-xs text-base-content/65">
						{t('filters.count', { shown: filtered.length, total: matchdays.length })}
					</span>
					{#if activeFilterCount > 0}
						<button type="button" class="btn btn-ghost btn-xs" onclick={clearFilters}>
							{t('import.clear')}
						</button>
					{/if}
				</div>
			</div>
		</div>

		{#if filtered.length === 0}
			<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
				{t('day.noneWithFilters')}
			</div>
		{:else}
			{#each paged as matchday, index (matchday.id)}
				<MatchdayCard
					{matchday}
					{editable}
					{showMismatch}
					{playerHref}
					{onEdit}
					{onDelete}
					open={index === 0}
				/>
			{/each}
			{#if filtered.length > shown}
				<button class="btn btn-block" onclick={() => (shown += PAGE)}>
					{t('filters.showMore', { count: filtered.length - shown })}
				</button>
			{/if}
		{/if}
	</div>
{/if}

<style>
	.list {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.fsummary {
		display: none;
		align-items: center;
		gap: 8px;
		width: 100%;
		min-height: 40px;
		background: none;
		border: 0;
		color: inherit;
		font: inherit;
		cursor: pointer;
	}
	.fs-label {
		flex: 1;
		text-align: left;
		font-weight: 600;
		font-size: 0.86rem;
	}
	.fs-caret {
		display: inline-flex;
		transition: transform 0.15s ease;
	}
	.fs-caret.open {
		transform: rotate(180deg);
	}
	.fbody {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.ftop {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		gap: 10px;
	}
	.frow {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
	}
	.flabel {
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-muted);
	}
	.fplayers {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.pchips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.pchip {
		cursor: pointer;
		min-height: 28px;
	}
	.pchip.sel {
		background: color-mix(in oklch, var(--color-primary) 18%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.fbottom {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	@media (max-width: 640px) {
		.fsummary {
			display: flex;
		}
		.fbody {
			display: none;
		}
		.fbody.open {
			display: flex;
			margin-top: 10px;
		}
	}
</style>
