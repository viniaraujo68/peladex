import { dev } from '$app/environment';
import { env } from '$env/dynamic/private';
import {
	DARK_THEME,
	LIGHT_THEME,
	parseThemePreference,
	THEME_COOKIE
} from '@viniaraujo68/plinth/theme';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
	const preference = parseThemePreference(event.cookies.get(THEME_COOKIE));
	const attribute =
		preference === 'light'
			? `data-theme="${LIGHT_THEME}"`
			: preference === 'dark'
				? `data-theme="${DARK_THEME}"`
				: '';

	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%peladex.theme%', attribute)
	});
}

const FALLBACK_BASE = dev ? 'http://localhost:8000' : 'http://backend:8000';

function apiBase() {
	return (env.PELADEX_API_INTERNAL_URL || FALLBACK_BASE).replace(/\/+$/, '');
}

/** @type {import('@sveltejs/kit').HandleFetch} */
export async function handleFetch({ request, fetch, event }) {
	const url = new URL(request.url);
	if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
		const proxied = new Request(apiBase() + url.pathname + url.search, request);
		let clientAddress = '';
		try {
			clientAddress = event.getClientAddress();
		} catch {
			clientAddress = '';
		}
		if (clientAddress) proxied.headers.set('X-Forwarded-For', clientAddress);
		return fetch(proxied);
	}
	return fetch(request);
}
