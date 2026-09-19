import { error } from '@sveltejs/kit';
import { fetchPublic } from '$lib/publicApi.js';

export const ssr = true;

/** @type {import('./$types').PageLoad} */
export async function load({ fetch, params, url }) {
	const token = url.searchParams.get('t');
	const query = token ? `?t=${encodeURIComponent(token)}` : '';
	const { data, status } = await fetchPublic(
		fetch,
		`/public/${encodeURIComponent(params.slug)}${query}`
	);

	if (status === 404) error(404, 'No public group with this slug.');

	return { group: data, status };
}
