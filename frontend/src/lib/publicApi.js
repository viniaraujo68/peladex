import { error } from '@sveltejs/kit';
import { dayTypeParam, dayTypeQuery } from './dayType.js';
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

/** @param {string|null} value */
function isoDate(value) {
	if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
	const parsed = new Date(`${value}T00:00:00Z`);
	return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value) ? value : '';
}

/** @param {URLSearchParams} params @returns {{ from: string, to: string }} */
export function periodParam(params) {
	return { from: isoDate(params.get('date_from')), to: isoDate(params.get('date_to')) };
}

/** @param {{ from: string, to: string }} period */
export function periodQuery(period) {
	return [period.from ? `date_from=${period.from}` : '', period.to ? `date_to=${period.to}` : '']
		.filter(Boolean)
		.join('&');
}

/** @param {{ fetch: typeof globalThis.fetch, params: { slug?: string }, url: URL }} event */
export async function loadPublicGroup({ fetch, params, url }) {
	const token = url.searchParams.get('t');
	const filters = [
		token ? `t=${encodeURIComponent(token)}` : '',
		dayTypeQuery(dayTypeParam(url.searchParams)),
		periodQuery(periodParam(url.searchParams))
	]
		.filter(Boolean)
		.join('&');
	const { data, status } = await fetchPublic(
		fetch,
		`/public/${encodeURIComponent(params.slug ?? '')}${filters ? `?${filters}` : ''}`
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
