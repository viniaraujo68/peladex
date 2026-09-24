import { error } from '@sveltejs/kit';
import { t } from './i18n.svelte.js';

/**
 * @param {typeof globalThis.fetch} fetch
 * @param {string} path
 * @returns {Promise<{ data: any, status: number }>}
 */
export async function fetchPublic(fetch, path) {
	try {
		const res = await fetch(`/api${path}`);
		if (!res.ok) return { data: null, status: res.status };
		return { data: await res.json(), status: 200 };
	} catch {
		return { data: null, status: 0 };
	}
}

/** @param {{ fetch: typeof globalThis.fetch, params: { slug?: string }, url: URL }} event */
export async function loadPublicGroup({ fetch, params, url }) {
	const token = url.searchParams.get('t');
	const query = token ? `?t=${encodeURIComponent(token)}` : '';
	const { data, status } = await fetchPublic(
		fetch,
		`/public/${encodeURIComponent(params.slug ?? '')}${query}`
	);
	if (status === 404) error(404, 'No public group with this slug.');
	return { group: data, status };
}

/** @param {number} status */
export function publicErrorMessage(status) {
	if (status === 200) return '';
	if (status === 403) return t('public.errorPrivate');
	if (status === 0) return t('error.body');
	return t('error.http', { status });
}
