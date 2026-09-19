import { goto } from '$app/navigation';
import { auth, logout } from '$lib/stores/auth.svelte.js';

const ROLE_USER = 'user';
const ROLE_GUEST = 'guest';

/** @param {string} role */
function holds(role) {
	if (!auth.ready) return false;
	return auth.user ? role === ROLE_USER : role === ROLE_GUEST;
}

/** @type {import('@viniaraujo68/plinth/user').UserContext} */
export const user = {
	get status() {
		if (!auth.ready) return 'loading';
		return auth.user ? 'authenticated' : 'anonymous';
	},
	get data() {
		return auth.user ? { name: auth.user.username, email: '' } : null;
	},
	hasRole: holds,
	hasAnyRole: (roles) => roles.length === 0 || roles.some(holds),
	hasAllRoles: (roles) => roles.every(holds),
	logout: async () => {
		await logout();
		await goto('/');
	}
};
