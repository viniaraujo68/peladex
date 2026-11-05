/** @typedef {{ home: number, away: number, homeScore: number, awayScore: number }} RotationMatch */
/** @typedef {{ stayers: number[], challengers: number[] }} NextMatch */

/**
 * @param {RotationMatch} match
 * @param {Map<number, number>} since
 * @param {RotationMatch|undefined} following
 * @returns {number|null}
 */
function stayerOf(match, since, following) {
	const { home, away } = match;
	if (following) {
		const carried = [home, away].filter(
			(team) => team === following.home || team === following.away
		);
		if (carried.length === 1) return carried[0];
	}
	if (match.homeScore > match.awayScore) return home;
	if (match.awayScore > match.homeScore) return away;
	const homeSince = since.get(home) ?? 0;
	const awaySince = since.get(away) ?? 0;
	if (homeSince === awaySince) return null;
	return homeSince > awaySince ? home : away;
}

/**
 * @param {number} teamCount
 * @param {RotationMatch[]} matches
 * @returns {NextMatch|null}
 */
export function nextMatch(teamCount, matches) {
	if (teamCount < 2) return null;
	/** @type {Set<number>} */
	const played = new Set();
	/** @type {number[]} */
	let queue = [];
	/** @type {Map<number, number>} */
	const since = new Map();
	/** @type {number[]} */
	let stayers = [];

	for (let index = 0; index < matches.length; index += 1) {
		const { home, away } = matches[index];
		if (home === away || home >= teamCount || away >= teamCount) continue;
		for (const team of [home, away]) if (!stayers.includes(team)) since.set(team, index);
		played.add(home);
		played.add(away);
		queue = queue.filter((team) => team !== home && team !== away);
		const stayer = stayerOf(matches[index], since, matches[index + 1]);
		stayers = stayer === null ? [home, away] : [stayer];
		if (stayer === null) queue.push(home, away);
		else queue.push(stayer === home ? away : home);
	}

	if (played.size === 0) return { stayers: [0], challengers: [1] };
	const fresh = Array.from({ length: teamCount }, (_, team) => team).filter(
		(team) => !played.has(team)
	);
	if (fresh.length) return { stayers, challengers: fresh };
	const waiting = queue.filter((team) => !stayers.includes(team));
	if (waiting.length) return { stayers, challengers: [waiting[0]] };
	return { stayers: [stayers[0]], challengers: [stayers[1]] };
}
