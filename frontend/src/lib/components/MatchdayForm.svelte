<script>
	import { tick } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { sortable } from '@viniaraujo68/plinth/attachments';
	import { Combobox, DragHandle, Select } from '@viniaraujo68/plinth/components';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { post, errorMessage } from '$lib/http.js';
	import { i18n, localeTag, t, teamName } from '$lib/i18n.svelte.js';
	import { nextMatch } from '$lib/rotation.js';
	import { explicitTeamColor } from '$lib/teamColor.js';
	import GoalMark from './GoalMark.svelte';
	import Icon from './Icon.svelte';
	import TeamCrest from './TeamCrest.svelte';

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

	const DEFAULT_TEAM_COLORS = ['black', 'white', 'red'];
	const TEAM_COLORS = [...DEFAULT_TEAM_COLORS, 'blue', 'green', 'yellow', 'gray'];
	const MAX_TEAMS = 20;
	const MAX_TEAM_PLAYERS = 40;
	const MAX_NOTES_LENGTH = 2000;

	/** @param {string} color */
	function colorName(color) {
		return t(`teamColor.${color}`);
	}

	/** @param {string} value */
	function fold(value) {
		return value
			.normalize('NFKD')
			.replace(/[̀-ͯ]/g, '')
			.replace(/\s+/g, ' ')
			.trim()
			.toLowerCase();
	}

	/** @param {string} value */
	function tidyName(value) {
		return value.replace(/\s+/g, ' ').trim().toLowerCase();
	}

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

	/** @typedef {{ key: number, name: string, color: string, playerIds: number[] }} TeamDraft */
	/** @typedef {{ playerId: number, ownGoal: boolean, assistId: number|null }} GoalDraft */
	/** @typedef {{ home: number, away: number, homeScore: number, awayScore: number, goals: GoalDraft[] }} MatchDraft */

	let teamKeys = 0;
	const nextTeamKey = () => ++teamKeys;

	/** @returns {TeamDraft[]} */
	function seedTeams() {
		if (matchday) {
			return matchday.standings
				.slice()
				.sort((a, b) => a.team_id - b.team_id)
				.map((s) => ({
					key: nextTeamKey(),
					name: teamName(s.name),
					color: explicitTeamColor(s.color),
					playerIds: s.members.map((m) => m.player_id)
				}));
		}
		return DEFAULT_TEAM_COLORS.map((color) => ({
			key: nextTeamKey(),
			name: colorName(color),
			color: '',
			playerIds: []
		}));
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
	let query = $state('');
	let addingPlayer = $state(false);

	let teams = $state(seedTeams());
	let matches = $state(seedMatches());
	// svelte-ignore state_referenced_locally
	let mvpId = $state(/** @type {string} */ (String(matchday?.mvp_player_id ?? '')));
	// svelte-ignore state_referenced_locally
	let notes = $state(matchday?.notes ?? '');

	let activeTeam = $state(0);
	let openMatches = $state(/** @type {number[]} */ ([]));
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

	const foldedQuery = $derived(fold(query));
	const exactPlayer = $derived(
		foldedQuery ? (players.find((p) => fold(p.name) === foldedQuery) ?? null) : null
	);
	const shownPlayers = $derived.by(() => {
		if (!foldedQuery) return rosterPlayers;
		const found = rosterPlayers.filter((p) => fold(p.name).includes(foldedQuery));
		return exactPlayer && !found.includes(exactPlayer) ? [exactPlayer, ...found] : found;
	});
	const pickTarget = $derived.by(() => {
		if (!foldedQuery) return null;
		if (exactPlayer) return exactPlayer;
		return shownPlayers.find((p) => !assigned.has(p.id)) ?? null;
	});
	const canCreate = $derived(!!foldedQuery && !exactPlayer);
	const enterCreates = $derived(canCreate && shownPlayers.length === 0);

	const freePresets = $derived.by(() => {
		const taken = new Set(teams.map((team) => tidyName(team.name)));
		return TEAM_COLORS.map(colorName).filter((preset) => !taken.has(preset));
	});

	const upcoming = $derived(nextMatch(teams.length, matches));
	const upcomingPairs = $derived(
		upcoming
			? upcoming.stayers.flatMap((home) => upcoming.challengers.map((away) => ({ home, away })))
			: []
	);
	const upcomingQuestion = $derived.by(() => {
		if (!upcoming || upcomingPairs.length < 2) return null;
		const stayerUnknown = upcoming.stayers.length > 1;
		const challengerUnknown = upcoming.challengers.length > 1;
		if (stayerUnknown && challengerUnknown) {
			return { title: t('day.whoNextBoth'), hint: t('day.whoNextBothHint') };
		}
		if (stayerUnknown) {
			return {
				title: t('day.whoStayed', { name: teamLabel(upcoming.challengers[0]) }),
				hint: t('day.whoStayedHint')
			};
		}
		return {
			title: t('day.whoEnters', { name: teamLabel(upcoming.stayers[0]) }),
			hint: t('day.whoEntersHint')
		};
	});

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
		return tidyName(teams[index]?.name ?? '') || `#${index + 1}`;
	}

	/** @param {number} index */
	function tidyTeamName(index) {
		if (teams[index]) teams[index].name = tidyName(teams[index].name);
	}

	/** @param {string} value */
	function pickDate(value) {
		date = value;
		showDateInput = false;
	}

	function addTeam() {
		const name = freePresets[Math.floor(Math.random() * freePresets.length)] ?? '';
		teams = [...teams, { key: nextTeamKey(), name, color: '', playerIds: [] }];
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
		openMatches = [];
		editingGoal = null;
	}

	/**
	 * @param {number} from
	 * @param {number} to
	 */
	function moveTeam(from, to) {
		if (from === to || to < 0 || to >= teams.length) return;
		const order = teams.map((_, index) => index);
		order.splice(to, 0, ...order.splice(from, 1));
		const position = new Map(order.map((previous, index) => [previous, index]));
		teams = order.map((previous) => teams[previous]);
		matches = matches.map((m) => ({
			...m,
			home: position.get(m.home) ?? m.home,
			away: position.get(m.away) ?? m.away
		}));
		activeTeam = position.get(activeTeam) ?? activeTeam;
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
	}

	/** @param {number} playerId */
	function pickPlayer(playerId) {
		togglePlayer(playerId);
		query = '';
	}

	/** @param {KeyboardEvent} ev */
	function onSearchKeydown(ev) {
		if (ev.key === 'Escape' && query) {
			ev.preventDefault();
			query = '';
			return;
		}
		if (ev.key !== 'Enter') return;
		ev.preventDefault();
		if (pickTarget) pickPlayer(pickTarget.id);
		else if (enterCreates) addPlayer();
	}

	/** @param {number} home @param {number} away */
	async function addMatch(home, away) {
		matches = [...matches, { home, away, homeScore: 0, awayScore: 0, goals: [] }];
		openMatches = [];
		editingGoal = null;
		await tick();
		document
			.getElementById(`match-${matches.length - 1}`)
			?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	/** @param {number} index */
	function isOpen(index) {
		return index === matches.length - 1 || openMatches.includes(index);
	}

	/** @param {number} index */
	function toggleMatch(index) {
		openMatches = openMatches.includes(index)
			? openMatches.filter((i) => i !== index)
			: [...openMatches, index];
		if (editingGoal?.match === index) editingGoal = null;
	}

	/** @param {number} index */
	function removeMatch(index) {
		matches = matches.filter((_, i) => i !== index);
		openMatches = openMatches.filter((i) => i !== index).map((i) => (i > index ? i - 1 : i));
		editingGoal = null;
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

	/** @param {number} team */
	function teamPlayers(team) {
		return (teams[team]?.playerIds ?? [])
			.map((id) => ({ id, name: nameById.get(id) ?? '?' }))
			.sort((a, b) => a.name.localeCompare(b.name, localeTag()));
	}

	/** @param {MatchDraft} match @param {number} playerId */
	function goalsBy(match, playerId) {
		return match.goals.filter((g) => g.playerId === playerId).length;
	}

	async function addPlayer() {
		const name = query.trim();
		if (!name || addingPlayer) return;
		addingPlayer = true;
		try {
			const created = await post(`/groups/${groupId}/players`, { name });
			players = [...players, { id: created.id, name: created.name, active: true }].sort((a, b) =>
				a.name.localeCompare(b.name, localeTag())
			);
			query = '';
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
		const names = teams.map((team) => tidyName(team.name)).filter(Boolean);
		if (new Set(names).size !== names.length) found.push(t('day.duplicateTeamName'));
		if (matches.some((m) => m.home === m.away)) found.push(t('day.sameTeamTwice'));
		if (teams.length > MAX_TEAMS) found.push(t('day.tooManyTeams', { max: MAX_TEAMS }));
		if (teams.some((team) => team.playerIds.length > MAX_TEAM_PLAYERS)) {
			found.push(t('day.tooManyPlayers', { max: MAX_TEAM_PLAYERS }));
		}
		if (matches.some((m) => m.goals.length > m.homeScore + m.awayScore)) {
			found.push(t('day.tooManyGoals'));
		}
		return found;
	});

	const mismatchCount = $derived(matches.filter(mismatched).length);

	const savedTeams = $derived.by(() => {
		const used = teams
			.map((_, index) => index)
			.filter(
				(index) =>
					teams[index].playerIds.length > 0 ||
					matches.some((m) => m.home === index || m.away === index)
			);
		return used.length >= 2 ? used : teams.map((_, index) => index);
	});

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
			teams: teams.map((team) => ({
				name: team.name,
				color: team.color,
				playerIds: [...team.playerIds]
			})),
			matches: matches.map((m) => ({ ...m, goals: m.goals.map((g) => ({ ...g })) }))
		};
	}

	const stateJson = $derived(JSON.stringify(formState()));
	let pristineJson = $state(JSON.stringify(formState()));
	let formLocale = i18n.locale;

	$effect(() => {
		const locale = i18n.locale;
		if (locale === formLocale) return;
		formLocale = locale;
		teams = teams.map((team) => ({ ...team, name: teamName(team.name) }));
		const pristine = JSON.parse(pristineJson);
		pristine.teams = pristine.teams.map((/** @type {TeamDraft} */ team) => ({
			...team,
			name: teamName(team.name)
		}));
		pristineJson = JSON.stringify(pristine);
	});
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
			key: nextTeamKey(),
			name: team.name ?? '',
			color: explicitTeamColor(team.color),
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
		openMatches = [];
		editingGoal = null;
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
		const position = new Map(savedTeams.map((teamIndex, index) => [teamIndex, index]));
		const payload = {
			date,
			venue_id: venueId ? Number(venueId) : null,
			mvp_player_id: mvpId ? Number(mvpId) : null,
			notes,
			teams: savedTeams.map((index) => ({
				name: tidyName(teams[index].name),
				color: teams[index].color,
				player_ids: [...teams[index].playerIds]
			})),
			matches: matches.map((m) => ({
				home_team_index: position.get(m.home) ?? m.home,
				away_team_index: position.get(m.away) ?? m.away,
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

		<div class="block">
			<label class="blabel" for="notes">
				{t('day.notes')}
				<span class="font-normal text-base-content/65">{t('common.optional')}</span>
			</label>
			<textarea
				id="notes"
				class="textarea w-full"
				rows="2"
				maxlength={MAX_NOTES_LENGTH}
				bind:value={notes}
			></textarea>
		</div>
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="sec-head">
			<h2 class="stitle">{t('day.teams')}</h2>
			<button
				type="button"
				class="btn btn-sm"
				disabled={teams.length >= MAX_TEAMS}
				onclick={addTeam}
			>
				{t('day.addTeam')}
			</button>
		</div>

		<div
			class="teamtabs"
			role="group"
			aria-label={t('day.teams')}
			{@attach sortable({ onmove: moveTeam })}
		>
			{#each teams as team, index (team.key)}
				<div class="teamtab" class:sel={activeTeam === index} data-sortable-item>
					{#if teams.length > 1}
						<DragHandle label={t('day.moveTeam', { name: teamLabel(index) })} />
					{/if}
					<button
						type="button"
						class="teamtab-pick"
						class:after-grip={teams.length > 1}
						aria-pressed={activeTeam === index}
						onclick={() => (activeTeam = index)}
					>
						<TeamCrest name={teamLabel(index)} color={team.color} />
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
					class="input w-full teamname"
					bind:value={teams[activeTeam].name}
					onblur={() => tidyTeamName(activeTeam)}
					maxlength="40"
					autocapitalize="none"
					autocomplete="off"
				/>
				{#if freePresets.length}
					<div class="chips" role="group" aria-label={t('day.teamPresets')}>
						{#each freePresets as preset (preset)}
							<button
								type="button"
								class="pchip"
								onclick={() => (teams[activeTeam].name = preset)}
							>
								<TeamCrest name={preset} />
								{preset}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<div class="block">
				<label class="blabel" for="player-search">
					{t('day.roster', { name: teamLabel(activeTeam) })}
				</label>
				<label class="input w-full">
					<Icon name="search" class="size-4 opacity-60" />
					<input
						id="player-search"
						type="search"
						class="grow"
						placeholder={t('day.playerSearch')}
						bind:value={query}
						onkeydown={onSearchKeydown}
						autocapitalize="none"
						autocomplete="off"
						enterkeyhint="done"
					/>
				</label>
				{#if rosterPlayers.length === 0 && !foldedQuery}
					<p class="hint">{t('day.noPlayersYet')}</p>
				{:else if shownPlayers.length}
					<div class="roster">
						{#each shownPlayers as player (player.id)}
							{@const teamIndex = assigned.get(player.id)}
							<button
								type="button"
								class="pchip"
								class:mine={teamIndex === activeTeam}
								class:taken={teamIndex !== undefined && teamIndex !== activeTeam}
								class:target={pickTarget?.id === player.id}
								aria-pressed={teamIndex === activeTeam}
								onclick={() => pickPlayer(player.id)}
							>
								{player.name}
								{#if teamIndex !== undefined && teamIndex !== activeTeam}
									<span class="ptag">{teamLabel(teamIndex)}</span>
								{/if}
							</button>
						{/each}
					</div>
				{:else}
					<p class="hint">{t('day.playerNoMatch')}</p>
				{/if}
				{#if canCreate}
					<button
						type="button"
						class="btn btn-sm btn-soft self-start"
						disabled={addingPlayer}
						onclick={addPlayer}
					>
						<Icon name="plus" class="size-4" />
						{t('day.createPlayer', { name: tidyName(query) })}
					</button>
				{/if}
				{#if pickTarget && assigned.get(pickTarget.id) === activeTeam}
					<p class="tiphint">{t('day.enterRemoves', { name: pickTarget.name })}</p>
				{:else if pickTarget}
					<p class="tiphint">{t('day.enterPicks', { name: pickTarget.name })}</p>
				{:else if enterCreates}
					<p class="tiphint">{t('day.enterCreates')}</p>
				{/if}
			</div>
		{/if}
	</section>

	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<h2 class="stitle">{t('day.matches')}</h2>

		{#each matches as match, index (index)}
			{#if !isOpen(index)}
				<button
					type="button"
					id="match-{index}"
					class="mfold"
					class:warn={mismatched(match)}
					aria-expanded="false"
					aria-label={t('day.expandMatch', { n: index + 1 })}
					onclick={() => toggleMatch(index)}
				>
					<span class="mnum">{index + 1}</span>
					<span class="fteam home">
						<span class="fname">{teamLabel(match.home)}</span>
						<TeamCrest name={teamLabel(match.home)} color={teams[match.home]?.color} />
					</span>
					<span class="fscore">{match.homeScore} x {match.awayScore}</span>
					<span class="fteam away">
						<TeamCrest name={teamLabel(match.away)} color={teams[match.away]?.color} />
						<span class="fname">{teamLabel(match.away)}</span>
					</span>
					<span class="fend">
						{#if mismatched(match)}
							<Icon name="warning" class="size-4 text-[var(--ink-warning)]" />
						{/if}
						<Icon name="chevron" class="size-3" />
					</span>
				</button>
			{:else}
				<div class="match" class:warn={mismatched(match)} id="match-{index}">
					<div class="mtop">
						<span class="mlabel">{t('day.matchNumber', { n: index + 1 })}</span>
						<span class="flex items-center gap-1">
							{#if index !== matches.length - 1}
								<button
									type="button"
									class="btn btn-ghost btn-xs"
									aria-expanded="true"
									onclick={() => toggleMatch(index)}
								>
									{t('day.collapseMatch')}
								</button>
							{/if}
							<button
								type="button"
								class="mx hit-44"
								aria-label={t('day.removeMatch')}
								onclick={() => removeMatch(index)}
							>
								<Icon name="close" class="size-4" />
							</button>
						</span>
					</div>
					<div class="mrow">
						<select class="select select-sm tsel home-team" bind:value={match.home}>
							{#each teams as _team, i (i)}
								<option value={i}>{teamLabel(i)}</option>
							{/each}
						</select>

						<div class="stepper home-score">
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

						<div class="stepper away-score">
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

						<select class="select select-sm tsel away-team" bind:value={match.away}>
							{#each teams as _team, i (i)}
								<option value={i}>{teamLabel(i)}</option>
							{/each}
						</select>
					</div>

					{#if match.home === match.away}
						<p class="mwarn">{t('day.sameTeamTwice')}</p>
					{:else if trackScorers}
						{#if teams[match.home]?.playerIds.length || teams[match.away]?.playerIds.length}
							<div class="sides">
								{#each [match.home, match.away] as team (team)}
									<div class="sidecol">
										<span class="sidehead">
											<TeamCrest name={teamLabel(team)} color={teams[team]?.color} />
											{teamLabel(team)}
										</span>
										<div class="scorers">
											{#each teamPlayers(team) as player (player.id)}
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
									</div>
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
			{/if}
		{/each}

		{#snippet pairLabel(/** @type {number} */ home, /** @type {number} */ away)}
			<span class="nextpair">
				<TeamCrest name={teamLabel(home)} color={teams[home]?.color} />
				{teamLabel(home)}
				<span class="xsep">x</span>
				{teamLabel(away)}
				<TeamCrest name={teamLabel(away)} color={teams[away]?.color} />
			</span>
		{/snippet}

		{#if upcomingPairs.length}
			<div class="nextmatch">
				{#if upcomingQuestion}
					<p class="nextq">{upcomingQuestion.title}</p>
					<p class="tiphint">{upcomingQuestion.hint}</p>
					<div class="nextchoices">
						{#each upcomingPairs as pair (`${pair.home}-${pair.away}`)}
							<button
								type="button"
								class="btn btn-soft btn-primary"
								onclick={() => addMatch(pair.home, pair.away)}
							>
								{@render pairLabel(pair.home, pair.away)}
							</button>
						{/each}
					</div>
				{:else}
					{@const pair = upcomingPairs[0]}
					<button
						type="button"
						class="btn btn-soft btn-primary nextbtn"
						onclick={() => addMatch(pair.home, pair.away)}
					>
						<Icon name="plus" class="size-4" />
						<span>{matches.length ? t('day.nextMatch') : t('day.firstMatch')}</span>
						{@render pairLabel(pair.home, pair.away)}
					</button>
					{#if matches.length}
						<p class="tiphint">{t('day.rotationHint')}</p>
					{/if}
				{/if}
			</div>
		{/if}
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
	.teamtab:global([data-sortable-dragging]) {
		border-color: var(--color-primary);
		box-shadow: 0 6px 16px color-mix(in oklch, var(--color-base-content) 22%, transparent);
		transform: scale(1.04);
	}
	.teamtab-pick.after-grip {
		padding-left: 2px;
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
	.pchip.target {
		outline: 2px solid var(--color-primary);
		outline-offset: 1px;
		opacity: 1;
	}
	.teamname {
		text-transform: lowercase;
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
	.match.warn,
	.mfold.warn {
		border-color: color-mix(in oklch, var(--color-warning) 55%, transparent);
	}
	.match,
	.mfold {
		scroll-margin-top: 80px;
	}
	.mtop {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin: -4px -4px -4px 0;
	}
	.mlabel {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.mfold {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 1fr) auto;
		align-items: center;
		gap: 8px;
		width: 100%;
		min-height: 44px;
		padding: 6px 12px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-base-content) 3%, transparent);
		color: var(--color-base-content);
		font: inherit;
		font-size: 0.84rem;
		text-align: left;
		cursor: pointer;
	}
	.mfold:hover {
		border-color: var(--color-primary);
	}
	.mnum {
		min-width: 1.6em;
		color: var(--ink-muted);
		font-size: 0.72rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.fteam {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}
	.fteam.home {
		justify-content: flex-end;
	}
	.fname {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.fscore {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.fend {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		color: var(--ink-muted);
	}
	.sides {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
	}
	.sidecol {
		display: flex;
		flex-direction: column;
		gap: 6px;
		min-width: 0;
	}
	.sidecol + .sidecol {
		padding-left: 12px;
		border-left: 1px solid color-mix(in oklch, var(--color-base-content) 9%, transparent);
	}
	.sidehead {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.72rem;
		font-weight: 700;
		color: var(--ink-muted);
	}
	.nextmatch {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.nextbtn {
		justify-content: flex-start;
		flex-wrap: wrap;
		height: auto;
		min-height: 48px;
		padding-block: 8px;
		gap: 8px;
	}
	.nextpair {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-weight: 700;
	}
	.nextq {
		font-size: 0.86rem;
		font-weight: 600;
	}
	.nextchoices {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.nextchoices :global(.btn) {
		flex: 1 1 140px;
	}
	.mrow {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		grid-template-areas:
			'home-team . away-team'
			'home-score sep away-score';
		align-items: center;
		gap: 8px 6px;
	}
	.home-team {
		grid-area: home-team;
	}
	.away-team {
		grid-area: away-team;
	}
	.home-score {
		grid-area: home-score;
		justify-self: center;
	}
	.away-score {
		grid-area: away-score;
		justify-self: center;
	}
	.mrow .xsep {
		grid-area: sep;
	}
	.tsel {
		width: 100%;
		min-width: 0;
	}
	@media (min-width: 640px) {
		.mrow {
			grid-template-columns: minmax(0, 1fr) auto auto auto minmax(0, 1fr);
			grid-template-areas: 'home-team home-score sep away-score away-team';
		}
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
