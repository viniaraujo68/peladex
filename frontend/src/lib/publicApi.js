import { error } from '@sveltejs/kit';

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
