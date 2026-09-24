<script>
	import { beforeNavigate } from '$app/navigation';
	import { Combobox, Select } from '@viniaraujo68/plinth/components';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { post, errorMessage } from '$lib/http.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import GoalMark from './GoalMark.svelte';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   groupId: number|string,
	 *   catalogs: { players: import('$lib/types.js').Player[], venues: import('$lib/types.js').Named[] },
	 *   matchday?: import('$lib/types.js').Matchday|null,
	 *   lastMatchday?: import('$lib/types.js').Matchday|null,
	 *   editing?: boolean,
	 *   saving?: boolean,
	 *   trackScorers?: boolean,
	 *   trackAssists?: boolean,
	 *   defaultVenueId?: number|null,
	 *   onsubmit: (payload: import('$lib/types.js').MatchdayPayload) => unknown,
	 *   oncancel: () => void
	 * }}
	 */
	let {
		groupId,
		catalogs,
		matchday = null,
		lastMatchday = null,
		editing = false,
		saving = false,
		trackScorers = true,
		trackAssists = false,
		defaultVenueId = null,
		onsubmit,
		oncancel
	} = $props();

	const TEAM_PRESETS = ['BRANCO', 'VERMELHO', 'AZUL', 'VERDE', 'PRETO', 'AMARELO'];

	/** @param {Date} d */
	function ymd(d) {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
			d.getDate()
		).padStart(2, '0')}`;
	}
	let now = $state(new Date());
	function refreshNow() {
		now = new Date();
	}
	const today = $derived(ymd(now));
	const yesterday = $derived(ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)));

	/** @typedef {{ name: string, color: string, playerIds: number[] }} TeamDraft */
	/** @typedef {{ playerId: number, ownGoal: boolean, assistId: number|null }} GoalDraft */
	/** @typedef {{ home: number, away: number, homeScore: number, awayScore: number, goals: GoalDraft[] }} MatchDraft */

	/** @returns {TeamDraft[]} */
	function seedTeams() {
		if (matchday) {
			return matchday.standings
				.slice()
				.sort((a, b) => a.team_id - b.team_id)
				.map((s) => ({
					name: s.name,
					color: s.color,
					playerIds: s.members.map((m) => m.player_id)
				}));
		}
		if (lastMatchday) {
			return lastMatchday.standings
				.slice()
				.sort((a, b) => a.team_id - b.team_id)
				.map((s) => ({ name: s.name, color: s.color, playerIds: [] }));
		}
		return [
			{ name: TEAM_PRESETS[0], color: '', playerIds: [] },
			{ name: TEAM_PRESETS[1], color: '', playerIds: [] }
		];
	}

	/** @returns {MatchDraft[]} */
	function seedMatches() {
		if (!matchday) return [];
		const order = matchday.standings
			.slice()
			.sort((a, b) => a.team_id - b.team_id)
			.map((s) => s.team_id);
		return matchday.matches.map((m) => ({
			home: order.indexOf(m.home_team_id),
			away: order.indexOf(m.away_team_id),
			homeScore: m.home_score,
			awayScore: m.away_score,
			goals: m.goals.map((g) => ({
				playerId: g.player_id,
				ownGoal: g.own_goal,
				assistId: g.assist_player_id
			}))
		}));
	}

	// svelte-ignore state_referenced_locally
	let date = $state(matchday?.date ?? today);
	// svelte-ignore state_referenced_locally
	let showDateInput = $state(
		!!matchday?.date && matchday.date !== today && matchday.date !== yesterday
	);
	// svelte-ignore state_referenced_locally
	let venues = $state([...catalogs.venues]);
	// svelte-ignore state_referenced_locally
	let venueId = $state(
		/** @type {string} */ (
			matchday
				? String(matchday.venue_id ?? '')
				: String(defaultVenueId ?? lastMatchday?.venue_id ?? '')
		)
	);
	let newVenue = $state('');
	let addingVenue = $state(false);
	let showNewVenue = $state(false);

	// svelte-ignore state_referenced_locally
	let players = $state([...catalogs.players]);
	let newPlayer = $state('');
	let addingPlayer = $state(false);

	let teams = $state(seedTeams());
	let matches = $state(seedMatches());
	// svelte-ignore state_referenced_locally
	let mvpId = $state(/** @type {string} */ (String(matchday?.mvp_player_id ?? '')));
	// svelte-ignore state_referenced_locally
	let notes = $state(matchday?.notes ?? '');

	let activeTeam = $state(0);
	let editingGoal = $state(/** @type {{ match: number, goal: number }|null} */ (null));
	let formError = $state('');
	let submitting = $state(false);

	const nameById = $derived(new Map(players.map((p) => [p.id, p.name])));
	const assigned = $derived.by(() => {
		/** @type {Map<number, number>} */
		const map = new Map();
		teams.forEach((team, index) => {
			for (const id of team.playerIds) map.set(id, index);
		});
		return map;
	});

	const rosterPlayers = $derived(players.filter((p) => p.active || assigned.has(p.id)));
	const playingIds = $derived([...assigned.keys()]);

	/** @type {import('@viniaraujo68/plinth/components').SelectOption[]} */
	const venueOptions = $derived(venues.map((v) => ({ value: String(v.id), label: v.name })));

	/** @type {import('@viniaraujo68/plinth/components').SelectOption[]} */
	const mvpOptions = $derived(
		playingIds
			.map((id) => ({ value: String(id), label: nameById.get(id) ?? '?' }))
			.sort((a, b) => a.label.localeCompare(b.label, localeTag()))
	);

	/** @param {number} index */
	function teamLabel(index) {
		return teams[index]?.name?.trim() || `#${index + 1}`;
	}

	/** @param {string} value */
	function pickDate(value) {
		date = value;
		showDateInput = false;
	}

	function addTeam() {
		const used = new Set(teams.map((team) => team.name.trim().toUpperCase()));
		const preset = TEAM_PRESETS.find((name) => !used.has(name)) ?? '';
		teams = [...teams, { name: preset, color: '', playerIds: [] }];
		activeTeam = teams.length - 1;
	}

	/** @param {number} index */
	function removeTeam(index) {
		teams = teams.filter((_, i) => i !== index);
		matches = matches
			.filter((m) => m.home !== index && m.away !== index)
			.map((m) => ({
				...m,
				home: m.home > index ? m.home - 1 : m.home,
				away: m.away > index ? m.away - 1 : m.away
			}));
		if (activeTeam >= teams.length) activeTeam = Math.max(0, teams.length - 1);
	}

	/** @param {number} playerId */
	function togglePlayer(playerId) {
		const current = assigned.get(playerId);
		teams = teams.map((team, index) => {
			if (index === current) {
				return { ...team, playerIds: team.playerIds.filter((id) => id !== playerId) };
			}
			if (index === activeTeam && current !== activeTeam) {
				return { ...team, playerIds: [...team.playerIds, playerId] };
			}
			return team;
		});
		if (current !== undefined && current !== activeTeam) return;
	}

	function addMatch() {
		if (teams.length < 2) return;
		const last = matches[matches.length - 1];
		const home = last ? last.away : 0;
		const away = last ? (last.away + 1) % teams.length : 1;
		matches = [
			...matches,
			{ home, away: away === home ? (home + 1) % teams.length : away, homeScore: 0, awayScore: 0, goals: [] }
		];
	}

	/** @param {number} index */
	function removeMatch(index) {
		matches = matches.filter((_, i) => i !== index);
	}

	/** @param {number} matchIndex @param {'home'|'away'} side @param {number} delta */
	function bumpScore(matchIndex, side, delta) {
		const key = side === 'home' ? 'homeScore' : 'awayScore';
		const next = Math.max(0, Math.min(99, matches[matchIndex][key] + delta));
		matches[matchIndex][key] = next;
	}

	/** @param {MatchDraft} match @param {GoalDraft} goal */
	function creditedSide(match, goal) {
		const team = assigned.get(goal.playerId);
		if (team === match.home) return goal.ownGoal ? 'away' : 'home';
		if (team === match.away) return goal.ownGoal ? 'home' : 'away';
		return null;
	}

	/** @param {MatchDraft} match @param {'home'|'away'|null} side @param {number} delta */
	function shiftScore(match, side, delta) {
		if (side === 'home') match.homeScore = Math.max(0, Math.min(99, match.homeScore + delta));
		else if (side === 'away') match.awayScore = Math.max(0, Math.min(99, match.awayScore + delta));
	}

	/** @param {number} matchIndex @param {number} playerId */
	function addGoal(matchIndex, playerId) {
		const match = matches[matchIndex];
		/** @type {GoalDraft} */
		const goal = { playerId, ownGoal: false, assistId: null };
		const side = creditedSide(match, goal);
		if (side === null) return;
		match.goals = [...match.goals, goal];
		shiftScore(match, side, 1);
	}

	/** @param {number} matchIndex @param {number} goalIndex */
	function removeGoal(matchIndex, goalIndex) {
		const match = matches[matchIndex];
		shiftScore(match, creditedSide(match, match.goals[goalIndex]), -1);
		match.goals = match.goals.filter((_, i) => i !== goalIndex);
		editingGoal = null;
	}

	/** @param {number} matchIndex @param {number} goalIndex */
	function toggleOwnGoal(matchIndex, goalIndex) {
		const match = matches[matchIndex];
		const goal = match.goals[goalIndex];
		shiftScore(match, creditedSide(match, goal), -1);
		goal.ownGoal = !goal.ownGoal;
		if (goal.ownGoal) goal.assistId = null;
		shiftScore(match, creditedSide(match, goal), 1);
	}

	/** @param {number} matchIndex @param {number} goalIndex @param {number|null} assistId */
	function setAssist(matchIndex, goalIndex, assistId) {
		const goal = matches[matchIndex].goals[goalIndex];
		goal.assistId = goal.assistId === assistId ? null : assistId;
	}

	/** @param {number} matchIndex @param {number} goalIndex */
	function openGoal(matchIndex, goalIndex) {
		editingGoal =
			editingGoal && editingGoal.match === matchIndex && editingGoal.goal === goalIndex
				? null
				: { match: matchIndex, goal: goalIndex };
	}

	/** @param {MatchDraft} match @param {GoalDraft} goal */
	function assistOptions(match, goal) {
		const team = assigned.get(goal.playerId);
		if (team === undefined) return [];
		return (teams[team]?.playerIds ?? [])
			.filter((id) => id !== goal.playerId)
			.map((id) => ({ id, name: nameById.get(id) ?? '?' }))
			.sort((a, b) => a.name.localeCompare(b.name, localeTag()));
	}

	/** @param {MatchDraft} match */
	function goalTally(match) {
		let home = 0;
		let away = 0;
		for (const goal of match.goals) {
			const team = assigned.get(goal.playerId);
			if (team === match.home) {
				if (goal.ownGoal) away++;
				else home++;
			} else if (team === match.away) {
				if (goal.ownGoal) home++;
				else away++;
			}
		}
		return { home, away };
	}

	/** @param {MatchDraft} match */
	function mismatched(match) {
		if (match.goals.length === 0) return false;
		const tally = goalTally(match);
		return tally.home !== match.homeScore || tally.away !== match.awayScore;
	}

	/** @param {MatchDraft} match */
	function matchPlayers(match) {
		const ids = [...(teams[match.home]?.playerIds ?? []), ...(teams[match.away]?.playerIds ?? [])];
		return ids
			.map((id) => ({ id, name: nameById.get(id) ?? '?', team: assigned.get(id) }))
			.sort((a, b) => a.name.localeCompare(b.name, localeTag()));
	}

	/** @param {MatchDraft} match @param {number} playerId */
	function goalsBy(match, playerId) {
		return match.goals.filter((g) => g.playerId === playerId).length;
	}

	async function addPlayer() {
		const name = newPlayer.trim();
		if (!name) return;
		addingPlayer = true;
		try {
			const created = await post(`/groups/${groupId}/players`, { name });
			players = [...players, { id: created.id, name: created.name, active: true }].sort((a, b) =>
				a.name.localeCompare(b.name, localeTag())
			);
			newPlayer = '';
			if (!assigned.has(created.id)) togglePlayer(created.id);
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			addingPlayer = false;
		}
	}

	async function addVenue() {
		const name = newVenue.trim();
		if (!name) return;
		addingVenue = true;
		try {
			const created = await post(`/groups/${groupId}/venues`, { name });
			venues = [...venues, created].sort((a, b) => a.name.localeCompare(b.name, localeTag()));
			venueId = String(created.id);
			newVenue = '';
			showNewVenue = false;
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			addingVenue = false;
		}
	}

	const problems = $derived.by(() => {
		/** @type {string[]} */
		const found = [];
		if (teams.length < 2) found.push(t('day.needTwoTeams'));
		if (teams.some((team) => !team.name.trim())) found.push(t('day.needTeamName'));
		const names = teams.map((team) => team.name.trim().toUpperCase()).filter(Boolean);
		if (new Set(names).size !== names.length) found.push(t('day.duplicateTeamName'));
		if (matches.some((m) => m.home === m.away)) found.push(t('day.sameTeamTwice'));
		return found;
	});

	const mismatchCount = $derived(matches.filter(mismatched).length);

	// svelte-ignore state_referenced_locally
	const draftKey = editing
		? `peladex.draft.matchday.edit.${matchday?.id}`
		: `peladex.draft.matchday.${groupId}`;

	function formState() {
		return {
			date,
			showDateInput,
			venueId,
			mvpId,
			notes,
			teams: teams.map((team) => ({ ...team, playerIds: [...team.playerIds] })),
			matches: matches.map((m) => ({ ...m, goals: m.goals.map((g) => ({ ...g })) }))
		};
	}

	const stateJson = $derived(JSON.stringify(formState()));
	const pristineJson = JSON.stringify(formState());
	const dirty = $derived(stateJson !== pristineJson);

	/** @type {{savedAt: string, state: any}|null} */
	let draftPrompt = $state(readDraft());

	function readDraft() {
		try {
			const raw = localStorage.getItem(draftKey);
			if (!raw) return null;
			const parsed = JSON.parse(raw);
			return parsed?.state ? parsed : null;
		} catch {
			return null;
		}
	}

	function clearDraft() {
		try {
			localStorage.removeItem(draftKey);
		} catch {
			// storage blocked
		}
	}

	function restoreDraft() {
		const s = draftPrompt?.state;
		draftPrompt = null;
		if (!s) return;
		date = s.date ?? date;
		showDateInput = date !== today && date !== yesterday;
		venueId = s.venueId ?? '';
		mvpId = s.mvpId ?? '';
		notes = s.notes ?? '';
		teams = (s.teams ?? []).map((/** @type {TeamDraft} */ team) => ({
			name: team.name ?? '',
			color: team.color ?? '',
			playerIds: [...(team.playerIds ?? [])]
		}));
		matches = (s.matches ?? []).map((/** @type {MatchDraft} */ m) => ({
			home: m.home ?? 0,
			away: m.away ?? 1,
			homeScore: m.homeScore ?? 0,
			awayScore: m.awayScore ?? 0,
			goals: (m.goals ?? []).map((g) => ({
				playerId: g.playerId,
				ownGoal: !!g.ownGoal,
				assistId: g.assistId ?? null
			}))
		}));
		activeTeam = 0;
	}

	function discardDraft() {
		draftPrompt = null;
		clearDraft();
	}

	$effect(() => {
		const json = stateJson;
		if (!dirty || draftPrompt || submitting) return;
		const timer = setTimeout(() => {
			try {
				localStorage.setItem(
					draftKey,
					JSON.stringify({ savedAt: new Date().toISOString(), state: JSON.parse(json) })
				);
			} catch {
				// storage blocked
			}
		}, 500);
		return () => clearTimeout(timer);
	});

	/** @param {string} iso */
	function draftDate(iso) {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleString(localeTag(), {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	beforeNavigate((nav) => {
		if (!dirty || submitting) return;
		if (!confirm(t('day.leaveConfirm'))) nav.cancel();
	});

	/** @param {BeforeUnloadEvent} ev */
	function onBeforeUnload(ev) {
		if (!dirty || submitting) return;
		ev.preventDefault();
		ev.returnValue = '';
	}

	function onVisibilityChange() {
		if (document.visibilityState === 'visible') refreshNow();
	}

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		formError = '';
		if (problems.length) {
			formError = problems[0];
			return;
		}
		submitting = true;
		const payload = {
			date,
			venue_id: venueId ? Number(venueId) : null,
			mvp_player_id: mvpId ? Number(mvpId) : null,
			notes,
			teams: teams.map((team) => ({
				name: team.name.trim(),
				color: team.color,
				player_ids: [...team.playerIds]
			})),
			matches: matches.map((m) => ({
				home_team_index: m.home,
				away_team_index: m.away,
				home_score: m.homeScore,
				away_score: m.awayScore,
				goals: m.goals.map((g) => ({
					player_id: g.playerId,
					own_goal: g.ownGoal,
					assist_player_id: trackAssists && !g.ownGoal ? g.assistId : null
				}))
			}))
		};
		const ok = await onsubmit(payload);
		if (ok === false) {
			submitting = false;
			return;
		}
		clearDraft();
	}
</script>

<svelte:window onbeforeunload={onBeforeUnload} onfocus={refreshNow} />
<svelte:document onvisibilitychange={onVisibilityChange} />

<form class="sheet" onsubmit={submit}>
	{#if draftPrompt}
		<div class="alert alert-soft alert-warning draft">
			<span>{t('day.draftFound', { date: draftDate(draftPrompt.savedAt) })}</span>
			<span class="flex items-center gap-2">
				<button type="button" class="btn btn-sm" onclick={restoreDraft}>
					{t('day.draftRestore')}
				</button>
				<button type="button" class="btn btn-sm" onclick={discardDraft}>
					{t('day.draftDiscard')}
				</button>
			</span>
		</div>
	{/if}

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="block">
			<span class="blabel" id="date-label">{t('day.date')}</span>
			<div class="chips" role="group" aria-labelledby="date-label">
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={!showDateInput && date === today}
					class:btn-primary={!showDateInput && date === today}
					onclick={() => pickDate(today)}
				>
					{t('day.today')}
				</button>
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={!showDateInput && date === yesterday}
					class:btn-primary={!showDateInput && date === yesterday}
					onclick={() => pickDate(yesterday)}
				>
					{t('day.yesterday')}
				</button>
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={showDateInput}
					class:btn-primary={showDateInput}
					onclick={() => (showDateInput = true)}
				>
					<Icon name="calendar" class="size-4" />
					{t('day.otherDate')}
				</button>
			</div>
			{#if showDateInput}
				<input
					class="input mt-2 w-full"
					type="date"
					aria-label={t('day.date')}
					bind:value={date}
					required
				/>
			{/if}
		</div>

		<div class="block">
			<span class="blabel" id="venue-label">{t('day.venue')}</span>
			<div class="venue-row">
				<Select
					options={venueOptions}
					bind:value={() => venueId, (value) => (venueId = value ?? '')}
					placeholder={t('day.noVenue')}
					clearable={venueId !== ''}
					clearLabel={t('common.remove')}
					aria-labelledby="venue-label"
					class="min-w-0 flex-1"
				/>
				<button type="button" class="btn btn-sm" onclick={() => (showNewVenue = !showNewVenue)}>
					{t('day.addVenue')}
				</button>
			</div>
			{#if showNewVenue}
				<div class="venue-row mt-2">
					<input
						class="input min-w-0 flex-1"
						placeholder={t('day.venuePlaceholder')}
						bind:value={newVenue}
					/>
					<button
						type="button"
						class="btn btn-sm btn-primary"
						disabled={addingVenue || !newVenue.trim()}
						onclick={addVenue}
					>
						{t('common.add')}
					</button>
				</div>
			{/if}
		</div>
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="sec-head">
			<h2 class="stitle">{t('day.teams')}</h2>
			<button type="button" class="btn btn-sm" onclick={addTeam}>{t('day.addTeam')}</button>
		</div>

		<div class="teamtabs" role="group" aria-label={t('day.teams')}>
			{#each teams as team, index (index)}
				<div class="teamtab" class:sel={activeTeam === index}>
					<button
						type="button"
						class="teamtab-pick"
						aria-pressed={activeTeam === index}
						onclick={() => (activeTeam = index)}
					>
						<span class="tname">{teamLabel(index)}</span>
						<span class="tcount">{team.playerIds.length}</span>
					</button>
					{#if teams.length > 2}
						<button
							type="button"
							class="teamtab-x hit-44"
							aria-label={t('day.removeTeam', { name: teamLabel(index) })}
							onclick={() => removeTeam(index)}
						>
							<Icon name="close" class="size-3" />
						</button>
					{/if}
				</div>
			{/each}
		</div>

		{#if teams[activeTeam]}
			<div class="block">
				<label class="blabel" for="team-name">{t('day.teamName')}</label>
				<input
					id="team-name"
					class="input w-full"
					bind:value={teams[activeTeam].name}
					maxlength="40"
				/>
			</div>

			<div class="block">
				<span class="blabel">{t('day.roster', { name: teamLabel(activeTeam) })}</span>
				{#if rosterPlayers.length === 0}
					<p class="hint">{t('day.noPlayersYet')}</p>
				{:else}
					<div class="roster">
						{#each rosterPlayers as player (player.id)}
							{@const teamIndex = assigned.get(player.id)}
							<button
								type="button"
								class="pchip"
								class:mine={teamIndex === activeTeam}
								class:taken={teamIndex !== undefined && teamIndex !== activeTeam}
								aria-pressed={teamIndex === activeTeam}
								onclick={() => togglePlayer(player.id)}
							>
								{player.name}
								{#if teamIndex !== undefined && teamIndex !== activeTeam}
									<span class="ptag">{teamLabel(teamIndex)}</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
				<div class="venue-row mt-3">
					<input
						class="input input-sm min-w-0 flex-1"
						placeholder={t('day.newPlayer')}
						bind:value={newPlayer}
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								addPlayer();
							}
						}}
					/>
					<button
						type="button"
						class="btn btn-sm"
						disabled={addingPlayer || !newPlayer.trim()}
						onclick={addPlayer}
					>
						{t('common.add')}
					</button>
				</div>
			</div>
		{/if}
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="sec-head">
			<h2 class="stitle">{t('day.matches')}</h2>
			<button type="button" class="btn btn-sm" disabled={teams.length < 2} onclick={addMatch}>
				{t('day.addMatch')}
			</button>
		</div>

		{#if matches.length === 0}
			<p class="hint">{t('day.noMatches')}</p>
		{/if}

		{#each matches as match, index (index)}
			<div class="match" class:warn={mismatched(match)}>
				<div class="mrow">
					<select class="select select-sm tsel" bind:value={match.home}>
						{#each teams as _team, i (i)}
							<option value={i}>{teamLabel(i)}</option>
						{/each}
					</select>

					<div class="stepper">
						<button
							type="button"
							class="stepbtn"
							aria-label="-"
							onclick={() => bumpScore(index, 'home', -1)}>−</button
						>
						<input
							class="scoreinput"
							type="number"
							min="0"
							max="99"
							inputmode="numeric"
							bind:value={match.homeScore}
							aria-label={t('standings.goalsFor')}
						/>
						<button
							type="button"
							class="stepbtn"
							aria-label="+"
							onclick={() => bumpScore(index, 'home', 1)}>+</button
						>
					</div>

					<span class="xsep">x</span>

					<div class="stepper">
						<button
							type="button"
							class="stepbtn"
							aria-label="-"
							onclick={() => bumpScore(index, 'away', -1)}>−</button
						>
						<input
							class="scoreinput"
							type="number"
							min="0"
							max="99"
							inputmode="numeric"
							bind:value={match.awayScore}
							aria-label={t('standings.goalsAgainst')}
						/>
						<button
							type="button"
							class="stepbtn"
							aria-label="+"
							onclick={() => bumpScore(index, 'away', 1)}>+</button
						>
					</div>

					<select class="select select-sm tsel" bind:value={match.away}>
						{#each teams as _team, i (i)}
							<option value={i}>{teamLabel(i)}</option>
						{/each}
					</select>

					<button
						type="button"
						class="mx hit-44"
						aria-label={t('day.removeMatch')}
						onclick={() => removeMatch(index)}
					>
						<Icon name="close" class="size-4" />
					</button>
				</div>

				{#if match.home === match.away}
					<p class="mwarn">{t('day.sameTeamTwice')}</p>
				{:else if trackScorers}
					{@const roster = matchPlayers(match)}
					{#if roster.length}
						<div class="scorers">
							{#each roster as player (player.id)}
								{@const count = goalsBy(match, player.id)}
								<button
									type="button"
									class="gchip"
									class:has={count > 0}
									onclick={() => addGoal(index, player.id)}
								>
									{player.name}
									{#if count > 0}<span class="gcount">{count}</span>{/if}
								</button>
							{/each}
						</div>
					{/if}
					{#if match.goals.length}
						<div class="goallist">
							{#each match.goals as goal, goalIndex (goalIndex)}
								{@const open =
									editingGoal?.match === index && editingGoal?.goal === goalIndex}
								<button
									type="button"
									class="goaltag"
									class:own={goal.ownGoal}
									class:open
									aria-expanded={open}
									onclick={() => openGoal(index, goalIndex)}
									title={t('day.editGoal', { name: nameById.get(goal.playerId) ?? '?' })}
								>
									<GoalMark
										player={nameById.get(goal.playerId) ?? '?'}
										assist={goal.assistId ? (nameById.get(goal.assistId) ?? '?') : null}
										ownGoal={goal.ownGoal}
										showAssist={trackAssists}
									/>
									<Icon name="chevron" class="size-3" />
								</button>
							{/each}
						</div>
						<p class="tiphint">{t('day.tapToEdit')}</p>
					{/if}

					{#if editingGoal?.match === index && match.goals[editingGoal.goal]}
						{@const goalIndex = editingGoal.goal}
						{@const goal = match.goals[goalIndex]}
						<div class="goaledit">
							<div class="ge-head">
								<span class="ge-title">
									{t('day.goalOf', { name: nameById.get(goal.playerId) ?? '?' })}
								</span>
								<button
									type="button"
									class="btn btn-ghost btn-xs"
									onclick={() => (editingGoal = null)}
								>
									{t('common.close')}
								</button>
							</div>

							<label class="check">
								<input
									type="checkbox"
									class="checkbox checkbox-sm"
									checked={goal.ownGoal}
									onchange={() => toggleOwnGoal(index, goalIndex)}
								/>
								<span>{t('day.markOwnGoal')}</span>
							</label>

							{#if trackAssists && !goal.ownGoal}
								<div class="block">
									<span class="blabel">{t('day.assist')}</span>
									<div class="scorers">
										<button
											type="button"
											class="gchip"
											class:has={goal.assistId === null}
											onclick={() => setAssist(index, goalIndex, null)}
										>
											{t('day.noAssist')}
										</button>
										{#each assistOptions(match, goal) as option (option.id)}
											<button
												type="button"
												class="gchip"
												class:has={goal.assistId === option.id}
												onclick={() => setAssist(index, goalIndex, option.id)}
											>
												{option.name}
											</button>
										{/each}
									</div>
									<p class="tiphint">{t('day.assistHint')}</p>
								</div>
							{/if}

							<button
								type="button"
								class="btn btn-soft btn-error btn-sm self-start"
								onclick={() => removeGoal(index, goalIndex)}
							>
								{t('day.removeGoal')}
							</button>
						</div>
					{/if}
				{/if}
			</div>
		{/each}
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="block">
			<span class="blabel" id="mvp-label">{t('day.mvp')}</span>
			<Combobox
				options={mvpOptions}
				bind:value={() => mvpId || null, (value) => (mvpId = value ?? '')}
				placeholder={t('day.mvpSearch')}
				emptyLabel={t('day.mvpNoMatch')}
				clearable={mvpId !== ''}
				clearLabel={t('common.remove')}
				aria-labelledby="mvp-label"
				class="w-full"
			/>
			<p class="hint">{t('day.mvpHint')}</p>
		</div>

		<div class="block">
			<label class="blabel" for="notes">
				{t('day.notes')}
				<span class="font-normal text-base-content/65">{t('common.optional')}</span>
			</label>
			<textarea id="notes" class="textarea w-full" rows="2" bind:value={notes}></textarea>
		</div>
	</section>

	<div class="savebar">
		<div class="savestatus">
			{#if problems.length}
				<span class="text-error">{problems[0]}</span>
			{:else if mismatchCount > 0}
				<span class="text-[var(--ink-warning)]">{t('day.goalMismatch')}</span>
			{:else}
				<span class="text-base-content/65">
					{t('day.matchCount', { count: matches.length })}
				</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<button type="button" class="btn" onclick={oncancel}>{t('common.cancel')}</button>
			<button class="btn btn-primary" disabled={saving || submitting || problems.length > 0}>
				{saving || submitting ? t('day.saving') : t('day.save')}
			</button>
		</div>
	</div>

	{#if formError}
		<div class="alert alert-soft alert-error">{formError}</div>
	{/if}
</form>

<style>
	.sheet {
		display: flex;
		flex-direction: column;
		gap: 16px;
		padding-bottom: 96px;
	}
	.draft {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.sec-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
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
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.tap {
		min-height: 40px;
	}
	.venue-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.teamtabs {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.teamtab {
		display: inline-flex;
		align-items: stretch;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 16%, transparent);
		border-radius: var(--radius-field);
		overflow: hidden;
		background: var(--color-base-100);
	}
	.teamtab.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 12%, transparent);
	}
	.teamtab-pick {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		min-height: 40px;
		padding: 0 12px;
		background: none;
		border: 0;
		color: inherit;
		font: inherit;
		font-size: 0.84rem;
		cursor: pointer;
	}
	.teamtab.sel .tname {
		font-weight: 700;
		color: var(--ink-primary);
	}
	.tcount {
		display: inline-grid;
		place-items: center;
		min-width: 1.5em;
		height: 1.5em;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
		font-size: 0.7rem;
		font-variant-numeric: tabular-nums;
	}
	.teamtab-x {
		display: grid;
		place-items: center;
		width: 28px;
		background: none;
		border: 0;
		border-left: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		color: var(--ink-muted);
		cursor: pointer;
	}
	.teamtab-x:hover {
		color: var(--color-error);
	}
	.roster {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.pchip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		min-height: 36px;
		padding: 5px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--color-base-content);
		font-size: 0.82rem;
		cursor: pointer;
	}
	.pchip.mine {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 16%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.pchip.taken {
		opacity: 0.6;
	}
	.ptag {
		font-size: 0.64rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-muted);
	}
	.match {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		border-radius: var(--radius-field);
	}
	.match.warn {
		border-color: color-mix(in oklch, var(--color-warning) 55%, transparent);
	}
	.mrow {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.tsel {
		flex: 1 1 110px;
		min-width: 92px;
	}
	.stepper {
		display: inline-flex;
		align-items: center;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 16%, transparent);
		border-radius: var(--radius-field);
		overflow: hidden;
	}
	.stepbtn {
		width: 32px;
		min-height: 36px;
		background: color-mix(in oklch, var(--color-base-content) 5%, transparent);
		border: 0;
		color: var(--color-base-content);
		font-size: 1rem;
		line-height: 1;
		cursor: pointer;
	}
	.stepbtn:hover {
		background: color-mix(in oklch, var(--color-primary) 16%, transparent);
	}
	.scoreinput {
		width: 42px;
		min-height: 36px;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		text-align: center;
		-moz-appearance: textfield;
		appearance: textfield;
	}
	.scoreinput::-webkit-outer-spin-button,
	.scoreinput::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}
	.xsep {
		color: var(--ink-muted);
		font-size: 0.8rem;
	}
	.mx {
		display: grid;
		place-items: center;
		width: 32px;
		min-height: 36px;
		margin-left: auto;
		background: none;
		border: 0;
		border-radius: var(--radius-field);
		color: var(--ink-muted);
		cursor: pointer;
	}
	.mx:hover {
		color: var(--color-error);
	}
	.scorers {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.gchip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		min-height: 32px;
		padding: 4px 10px;
		border: 1px dashed color-mix(in oklch, var(--color-base-content) 22%, transparent);
		border-radius: var(--radius-field);
		background: none;
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.gchip:hover {
		color: var(--color-base-content);
		border-color: var(--color-primary);
	}
	.gchip.has {
		border-style: solid;
		color: var(--color-base-content);
	}
	.gcount {
		display: inline-grid;
		place-items: center;
		min-width: 1.35em;
		height: 1.35em;
		border-radius: 999px;
		background: var(--color-primary);
		color: var(--color-primary-content);
		font-size: 0.66rem;
		font-weight: 700;
	}
	.goallist {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		padding-top: 8px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 9%, transparent);
	}
	.goaltag {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		min-height: 28px;
		padding: 3px 9px;
		border: 0;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-size: 0.74rem;
		font-weight: 600;
		cursor: pointer;
	}
	.goaltag.own {
		background: color-mix(in oklch, var(--color-warning) 18%, transparent);
		color: var(--ink-warning);
	}
	.goaltag.open {
		outline: 2px solid var(--color-primary);
		outline-offset: 1px;
	}
	.tiphint {
		font-size: 0.7rem;
		color: var(--ink-muted);
	}
	.goaledit {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-top: 4px;
		padding: 12px;
		border: 1px solid color-mix(in oklch, var(--color-primary) 40%, transparent);
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-primary) 6%, transparent);
	}
	.ge-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	.ge-title {
		font-weight: 700;
		font-size: 0.86rem;
	}
	.check {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 0.84rem;
		cursor: pointer;
	}
	.mwarn {
		font-size: 0.76rem;
		color: var(--color-error);
	}
	.savebar {
		position: sticky;
		bottom: 0;
		z-index: 20;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		margin: 0 -20px -96px;
		padding: 12px 20px calc(12px + env(safe-area-inset-bottom));
		background: color-mix(in oklch, var(--color-base-100) 92%, transparent);
		backdrop-filter: blur(10px);
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
	}
	.savestatus {
		font-size: 0.8rem;
		min-width: 0;
		flex: 1 1 140px;
	}
	@media (max-width: 560px) {
		.savebar :global(.btn) {
			flex: 1;
		}
	}
</style>
