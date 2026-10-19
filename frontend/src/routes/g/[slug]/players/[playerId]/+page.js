import { error } from '@sveltejs/kit';
import { dayTypeParam, dayTypeQuery } from '$lib/dayType.js';
import { fetchPublic } from '$lib/publicApi.js';

export const ssr = true;

/** @type {import('./$types').PageLoad} */
export async function load({ fetch, params, url }) {
	const token = url.searchParams.get('t');
	const tokenQuery = token ? `t=${encodeURIComponent(token)}` : '';
	const slug = encodeURIComponent(params.slug);
	const minDays = url.searchParams.get('min') ?? '3';
	const filterQuery = [tokenQuery, dayTypeQuery(dayTypeParam(url.searchParams))]
		.filter(Boolean)
		.join('&');

	const detailQuery = [filterQuery, `min_days=${encodeURIComponent(minDays)}`]
		.filter(Boolean)
		.join('&');

	const [detail, group] = await Promise.all([
		fetchPublic(fetch, `/public/${slug}/players/${params.playerId}?${detailQuery}`),
		fetchPublic(fetch, `/public/${slug}${filterQuery ? `?${filterQuery}` : ''}`)
	]);

	if (detail.status === 404) error(404, 'No such player in this public group.');

	return {
		detail: detail.data,
		group: group.data,
		status: detail.status === 200 ? group.status : detail.status,
		minDays: Number(minDays) || 3
	};
}
