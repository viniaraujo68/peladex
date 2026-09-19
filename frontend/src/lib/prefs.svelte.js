const PREFIX = 'peladex.opt.mismatchBadge';

/** @type {Record<string, boolean>} */
const overrides = $state({});

/** @param {string|number} groupId */
function key(groupId) {
	return `${PREFIX}.${groupId}`;
}

/** @param {string|number} groupId */
function readStored(groupId) {
	try {
		return localStorage.getItem(key(groupId)) !== '0';
	} catch {
		return true;
	}
}

/** @param {string|number} groupId */
export function mismatchBadgeEnabled(groupId) {
	return overrides[String(groupId)] ?? readStored(groupId);
}

/** @param {string|number} groupId @param {boolean} on */
export function setMismatchBadge(groupId, on) {
	overrides[String(groupId)] = on;
	try {
		localStorage.setItem(key(groupId), on ? '1' : '0');
	} catch {
		// storage blocked
	}
}
