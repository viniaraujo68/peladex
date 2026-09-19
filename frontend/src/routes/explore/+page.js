import { fetchPublic } from '$lib/publicApi.js';

export const ssr = true;

/** @type {import('./$types').PageLoad} */
export async function load({ fetch }) {
	const { data, status } = await fetchPublic(fetch, '/public?q=');
	return { groups: data ?? [], status };
}
