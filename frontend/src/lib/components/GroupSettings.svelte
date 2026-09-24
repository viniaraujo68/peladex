<script>
	import { goto } from '$app/navigation';
	import { Copyable, Select } from '@viniaraujo68/plinth/components';
	import { confirm } from '@viniaraujo68/plinth/confirm';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { page } from '$app/stores';
	import { del, get, patch, post, errorMessage } from '$lib/http.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { mismatchBadgeEnabled, setMismatchBadge } from '$lib/prefs.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   group: import('$lib/types.js').Group,
	 *   onchange: (updated?: import('$lib/types.js').Group) => void
	 * }}
	 */
	let { group, onchange } = $props();

	// svelte-ignore state_referenced_locally
	let name = $state(group.name);
	// svelte-ignore state_referenced_locally
	let description = $state(group.description);
	// svelte-ignore state_referenced_locally
	let visibility = $state(group.visibility);
	// svelte-ignore state_referenced_locally
	let winPoints = $state(group.win_points);
	// svelte-ignore state_referenced_locally
	let drawPoints = $state(group.draw_points);
	// svelte-ignore state_referenced_locally
	let lossPoints = $state(group.loss_points);
	// svelte-ignore state_referenced_locally
	let trackScorers = $state(group.track_scorers);
	// svelte-ignore state_referenced_locally
	let trackAssists = $state(group.track_assists);
	// svelte-ignore state_referenced_locally
	let showRatings = $state(group.show_ratings);
	// svelte-ignore state_referenced_locally
	let defaultVenueId = $state(String(group.default_venue_id ?? ''));
	let saving = $state(false);
	let error = $state('');

	let players = $state(/** @type {import('$lib/types.js').Player[]} */ ([]));
	let venues = $state(/** @type {import('$lib/types.js').Named[]} */ ([]));
	let newPlayer = $state('');
	let editingId = $state(/** @type {number|null} */ (null));
	let editingName = $state('');
	let newVenue = $state('');
	let loading = $state(true);

	const mismatchOn = $derived(mismatchBadgeEnabled(group.id));

	const shareUrl = $derived.by(() => {
		const origin = $page.url.origin;
		if (group.visibility === 'public') return `${origin}/g/${group.slug}`;
		if (group.share_token) return `${origin}/g/${group.slug}?t=${group.share_token}`;
		return '';
	});

	const dirty = $derived(
		name !== group.name ||
			description !== group.description ||
			visibility !== group.visibility ||
			winPoints !== group.win_points ||
			drawPoints !== group.draw_points ||
			lossPoints !== group.loss_points ||
			trackScorers !== group.track_scorers ||
			trackAssists !== group.track_assists ||
			showRatings !== group.show_ratings ||
			defaultVenueId !== String(group.default_venue_id ?? '')
	);

	/** @type {import('@viniaraujo68/plinth/components').SelectOption[]} */
	const venueOptions = $derived(venues.map((v) => ({ value: String(v.id), label: v.name })));

	$effect(() => {
		load();
	});

	async function load() {
		loading = true;
		try {
			[players, venues] = await Promise.all([
				get(`/groups/${group.id}/players`),
				get(`/groups/${group.id}/venues`)
			]);
		} catch (e) {
			error = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	async function save() {
		saving = true;
		error = '';
		try {
			const updated = await patch(`/groups/${group.id}`, {
				name,
				description,
				visibility,
				win_points: winPoints,
				draw_points: drawPoints,
				loss_points: lossPoints,
				track_scorers: trackScorers,
				track_assists: trackAssists && trackScorers,
				show_ratings: showRatings,
				default_venue_id: defaultVenueId ? Number(defaultVenueId) : null
			});
			toast.success(t('toast.settingsSaved'));
			onchange(updated);
		} catch (e) {
			error = errorMessage(e);
		} finally {
			saving = false;
		}
	}

	async function addPlayer() {
		const value = newPlayer.trim();
		if (!value) return;
		try {
			const created = await post(`/groups/${group.id}/players`, { name: value });
			players = [...players, created].sort((a, b) => a.name.localeCompare(b.name, localeTag()));
			newPlayer = '';
			toast.success(t('toast.playerAdded', { name: created.name }));
			onchange();
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {import('$lib/types.js').Player} player */
	async function removePlayer(player) {
		try {
			await del(`/groups/${group.id}/players/${player.id}`);
			await load();
			onchange();
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {import('$lib/types.js').Player} player */
	function startRename(player) {
		editingId = player.id;
		editingName = player.name;
	}

	function cancelRename() {
		editingId = null;
		editingName = '';
	}

	/** @param {import('$lib/types.js').Player} player */
	async function renamePlayer(player) {
		if (editingId !== player.id) return;
		const value = editingName.trim();
		if (!value || value.toLowerCase() === player.name) {
			cancelRename();
			return;
		}
		try {
			const updated = await patch(`/groups/${group.id}/players/${player.id}`, { name: value });
			players = players
				.map((p) => (p.id === player.id ? { ...p, name: updated.name } : p))
				.sort((a, b) => a.name.localeCompare(b.name, localeTag()));
			toast.success(t('toast.playerRenamed', { from: player.name, to: updated.name }));
			cancelRename();
			onchange();
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {HTMLInputElement} node */
	function autofocus(node) {
		node.focus();
		node.select();
	}

	/** @param {import('$lib/types.js').Player} player */
	async function reactivate(player) {
		try {
			await patch(`/groups/${group.id}/players/${player.id}`, { active: true });
			players = players.map((p) => (p.id === player.id ? { ...p, active: true } : p));
			toast.success(t('toast.playerReactivated', { name: player.name }));
			onchange();
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	async function addVenue() {
		const value = newVenue.trim();
		if (!value) return;
		try {
			const created = await post(`/groups/${group.id}/venues`, { name: value });
			venues = [...venues, created].sort((a, b) => a.name.localeCompare(b.name, localeTag()));
			newVenue = '';
			toast.success(t('toast.venueAdded', { name: created.name }));
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {import('$lib/types.js').Named} venue */
	async function removeVenue(venue) {
		try {
			await del(`/groups/${group.id}/venues/${venue.id}`);
			venues = venues.filter((v) => v.id !== venue.id);
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	async function rotateToken() {
		try {
			const updated = await post(`/groups/${group.id}/rotate-share-token`);
			toast.success(t('toast.tokenRotated'));
			onchange(updated);
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	async function removeGroup() {
		const confirmed = await confirm({
			title: t('settings.deleteGroup'),
			description: t('settings.deleteConfirmBody', { name: group.name }),
			confirmLabel: t('settings.deletePermanently'),
			challenge: group.name,
			danger: true
		});
		if (!confirmed) return;
		try {
			await del(`/groups/${group.id}`);
			await goto('/');
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}
</script>

<div class="settings">
	{#if error}<div class="alert alert-soft alert-error">{error}</div>{/if}

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<h3 class="stitle">{t('settings.group')}</h3>
		<div class="block">
			<label class="blabel" for="s-name">{t('common.name')}</label>
			<input id="s-name" class="input w-full" bind:value={name} />
			{#if name.trim() && name !== group.name}
				<span class="hint">{t('settings.renameMovesLink')}</span>
			{/if}
		</div>
		<div class="block">
			<label class="blabel" for="s-desc">{t('common.description')}</label>
			<input id="s-desc" class="input w-full" bind:value={description} />
		</div>
		<div class="block">
			<span class="blabel">{t('group.visibility')}</span>
			<div class="vis">
				<button
					type="button"
					class="vis-opt"
					class:sel={visibility === 'public'}
					onclick={() => (visibility = 'public')}
				>
					<Icon name="globe" class="size-5" />
					<span class="font-semibold">{t('group.public')}</span>
					<span class="vis-d">{t('group.publicHint')}</span>
				</button>
				<button
					type="button"
					class="vis-opt"
					class:sel={visibility === 'private'}
					onclick={() => (visibility = 'private')}
				>
					<Icon name="lock" class="size-5" />
					<span class="font-semibold">{t('group.private')}</span>
					<span class="vis-d">{t('group.privateHint')}</span>
				</button>
			</div>
		</div>

		<div class="block">
			<span class="blabel">{t('settings.tracking')}</span>
			<label class="check">
				<input type="checkbox" class="checkbox checkbox-sm" bind:checked={trackScorers} />
				<span>
					{t('settings.trackScorers')}
					<span class="hint block">{t('settings.trackScorersHint')}</span>
				</span>
			</label>
			<label class="check" class:disabled={!trackScorers}>
				<input
					type="checkbox"
					class="checkbox checkbox-sm"
					bind:checked={trackAssists}
					disabled={!trackScorers}
				/>
				<span>
					{t('settings.trackAssists')}
					<span class="hint block">
						{trackScorers
							? t('settings.trackAssistsHint')
							: t('settings.trackAssistsNeedsScorers')}
					</span>
				</span>
			</label>
			<label class="check">
				<input type="checkbox" class="checkbox checkbox-sm" bind:checked={showRatings} />
				<span>
					{t('settings.showRatings')}
					<span class="hint block">{t('settings.showRatingsHint')}</span>
				</span>
			</label>
		</div>

		<div class="block">
			<span class="blabel">{t('settings.points')}</span>
			<div class="points">
				<label class="pt">
					<span>{t('settings.winPoints')}</span>
					<input class="input input-sm" type="number" min="0" max="10" bind:value={winPoints} />
				</label>
				<label class="pt">
					<span>{t('settings.drawPoints')}</span>
					<input class="input input-sm" type="number" min="0" max="10" bind:value={drawPoints} />
				</label>
				<label class="pt">
					<span>{t('settings.lossPoints')}</span>
					<input class="input input-sm" type="number" min="0" max="10" bind:value={lossPoints} />
				</label>
			</div>
			<p class="hint">{t('settings.pointsHint')}</p>
		</div>

		<button class="btn btn-primary self-start" disabled={saving || !dirty} onclick={save}>
			{saving ? t('common.saving') : t('settings.saveChanges')}
		</button>
	</section>

	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<h3 class="stitle">{t('settings.publicLink')}</h3>
		{#if dirty && visibility !== group.visibility}
			<p class="hint">{t('settings.linkUnsavedHint')}</p>
		{/if}
		{#if shareUrl}
			<Copyable
				copyableText={shareUrl}
				copyLabel={t('common.copy')}
				copiedLabel={t('toast.linkCopied')}
				class="sharelink"
			>
				<span class="sharetext">{shareUrl}</span>
			</Copyable>
			<p class="hint">
				{group.visibility === 'public'
					? t('settings.publicLinkHint')
					: t('settings.privateLinkHint')}
			</p>
			{#if group.visibility === 'private'}
				<button class="btn btn-sm self-start" onclick={rotateToken}>
					{t('settings.rotateToken')}
				</button>
			{/if}
		{:else}
			<p class="hint">{t('settings.noLinkYet')}</p>
			<button class="btn btn-sm self-start" onclick={rotateToken}>
				{t('settings.generateLink')}
			</button>
		{/if}
	</section>

	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<h3 class="stitle">{t('settings.options')}</h3>
		<label class="check">
			<input
				type="checkbox"
				class="checkbox checkbox-sm"
				checked={mismatchOn}
				onchange={(e) => setMismatchBadge(group.id, e.currentTarget.checked)}
			/>
			<span>
				{t('settings.mismatchOption')}
				<span class="hint block">{t('settings.mismatchOptionHint')}</span>
			</span>
		</label>
	</section>

	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<h3 class="stitle">{t('settings.players')}</h3>
		{#if loading}
			<p class="hint">{t('common.loading')}</p>
		{:else if players.length === 0}
			<p class="hint">{t('settings.noPlayers')}</p>
		{:else}
			<div class="names">
				{#each players as player (player.id)}
					{#if editingId === player.id}
						<span class="nchip editing">
							<input
								class="rename"
								aria-label={t('settings.renamePlayer', { name: player.name })}
								bind:value={editingName}
								use:autofocus
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										renamePlayer(player);
									} else if (e.key === 'Escape') {
										cancelRename();
									}
								}}
								onblur={() => renamePlayer(player)}
							/>
						</span>
					{:else}
						<span class="nchip" class:off={!player.active}>
							{player.name}
							<button
								type="button"
								class="nx edit hit-44"
								aria-label={t('settings.renamePlayer', { name: player.name })}
								onclick={() => startRename(player)}
							>
								<Icon name="edit" class="size-3" />
							</button>
							{#if player.active}
								<button
									type="button"
									class="nx hit-44"
									aria-label={t('common.remove')}
									onclick={() => removePlayer(player)}
								>
									<Icon name="close" class="size-3" />
								</button>
							{:else}
								<button
									type="button"
									class="nx hit-44"
									aria-label={t('settings.reactivate', { name: player.name })}
									onclick={() => reactivate(player)}
								>
									<Icon name="restore" class="size-3" />
								</button>
							{/if}
						</span>
					{/if}
				{/each}
			</div>
			{#if players.some((p) => !p.active)}
				<p class="hint">{t('settings.inactiveHint')}</p>
			{/if}
		{/if}
		<div class="addrow">
			<input
				class="input input-sm min-w-0 flex-1"
				placeholder={t('settings.playerPlaceholder')}
				bind:value={newPlayer}
				onkeydown={(e) => {
					if (e.key === 'Enter') {
						e.preventDefault();
						addPlayer();
					}
				}}
			/>
			<button class="btn btn-sm" disabled={!newPlayer.trim()} onclick={addPlayer}>
				{t('common.add')}
			</button>
		</div>
	</section>

	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<h3 class="stitle">{t('settings.venues')}</h3>
		{#if venues.length}
			<div class="names">
				{#each venues as venue (venue.id)}
					<span class="nchip">
						{venue.name}
						<button
							type="button"
							class="nx hit-44"
							aria-label={t('common.remove')}
							onclick={() => removeVenue(venue)}
						>
							<Icon name="close" class="size-3" />
						</button>
					</span>
				{/each}
			</div>
		{/if}
		<div class="addrow">
			<input
				class="input input-sm min-w-0 flex-1"
				placeholder={t('settings.addPlaceholder')}
				bind:value={newVenue}
				onkeydown={(e) => {
					if (e.key === 'Enter') {
						e.preventDefault();
						addVenue();
					}
				}}
			/>
			<button class="btn btn-sm" disabled={!newVenue.trim()} onclick={addVenue}>
				{t('common.add')}
			</button>
		</div>

		{#if venues.length}
			<div class="block">
				<span class="blabel" id="dv-label">{t('settings.defaultVenue')}</span>
				<Select
					options={venueOptions}
					bind:value={() => defaultVenueId, (value) => (defaultVenueId = value ?? '')}
					placeholder={t('settings.noDefaultVenue')}
					clearable={defaultVenueId !== ''}
					clearLabel={t('common.remove')}
					aria-labelledby="dv-label"
					class="w-full max-w-sm"
				/>
				<p class="hint">{t('settings.defaultVenueHint')}</p>
			</div>
		{/if}
	</section>

	<section class="card danger flex flex-col gap-3 bg-base-100 p-5">
		<h3 class="stitle text-error">{t('settings.dangerZone')}</h3>
		<p class="hint">
			{t('settings.deleteWarningPre')}
			<b>{t('settings.deleteWarningStrong')}</b>
			{t('settings.deleteWarningPost')}
		</p>
		<button class="btn btn-error btn-soft self-start" onclick={removeGroup}>
			{t('settings.deleteGroup')}
		</button>
	</section>
</div>

<style>
	.settings {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.stitle {
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.block {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.blabel {
		font-size: 0.72rem;
		font-weight: 600;
		color: color-mix(in oklch, var(--color-base-content) 82%, transparent);
	}
	.hint {
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.vis {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	@media (max-width: 560px) {
		.vis {
			grid-template-columns: 1fr;
		}
	}
	.vis-opt {
		display: flex;
		flex-direction: column;
		gap: 3px;
		text-align: left;
		padding: 12px 14px;
		border-radius: var(--radius-field);
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		background: var(--color-base-100);
		color: var(--color-base-content);
		cursor: pointer;
	}
	.vis-opt.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 12%, transparent);
	}
	.vis-opt :global(svg) {
		margin-bottom: 2px;
		color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
	}
	.vis-opt.sel :global(svg) {
		color: var(--ink-primary);
	}
	.vis-d {
		font-size: 0.74rem;
		line-height: 1.3;
		color: var(--ink-muted);
	}
	.points {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}
	.pt {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 0.74rem;
		color: var(--ink-muted);
	}
	.pt input {
		width: 5rem;
	}
	.check {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		font-size: 0.86rem;
		cursor: pointer;
	}
	.check.disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.names {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.nchip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		min-height: 32px;
		padding: 4px 6px 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		font-size: 0.82rem;
	}
	.nchip.off {
		opacity: 0.55;
		border-style: dashed;
	}
	.nx {
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		border: 0;
		border-radius: 999px;
		background: none;
		color: var(--ink-muted);
		cursor: pointer;
	}
	.nx:hover {
		color: var(--color-error);
	}
	.nx.edit:hover {
		color: var(--ink-primary);
	}
	.nchip.editing {
		padding: 2px 4px;
		border-color: var(--color-primary);
	}
	.rename {
		width: 12ch;
		min-height: 26px;
		padding: 0 6px;
		border: 0;
		background: none;
		font: inherit;
		outline: none;
	}
	.addrow {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.danger {
		border-color: color-mix(in oklch, var(--color-error) 35%, transparent);
	}
	:global(.sharelink) {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
		padding: 8px 10px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
	}
	.sharetext {
		min-width: 0;
		overflow-wrap: anywhere;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.76rem;
	}
</style>
