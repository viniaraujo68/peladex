import { get, post } from '$lib/http.js';

export const auth = $state({
	user: /** @type {{id:number, username:string}|null} */ (null),
	ready: false
});

export async function loadUser() {
	try {
		auth.user = await get('/auth/me');
	} catch {
		auth.user = null;
	} finally {
		auth.ready = true;
	}
}

/** @param {string} username @param {string} password */
export async function login(username, password) {
	auth.user = await post('/auth/login', { username, password });
}

/** @param {string} username @param {string} password */
export async function register(username, password) {
	auth.user = await post('/auth/register', { username, password });
}

export async function logout() {
	await post('/auth/logout');
	auth.user = null;
}

/** @param {string} currentPassword @param {string} newPassword */
export async function changePassword(currentPassword, newPassword) {
	await post('/auth/change-password', {
		current_password: currentPassword,
		new_password: newPassword
	});
}

export async function logoutEverywhere() {
	await post('/auth/logout-all');
	auth.user = null;
}
