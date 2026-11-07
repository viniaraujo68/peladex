import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').PageLoad} */
export function load({ params, url }) {
	const query = new URLSearchParams(url.searchParams);
	query.set('tab', 'combos');
	redirect(308, `/g/${encodeURIComponent(params.slug)}?${query}`);
}
