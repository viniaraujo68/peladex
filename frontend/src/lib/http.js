import { createHttpClient, errorMessage, errorStatus } from '@viniaraujo68/plinth/http';
import { t } from './i18n.svelte.js';

/** @param {any} detail */
function detailMessage(detail) {
	if (Array.isArray(detail)) {
		return detail
			.map((d) => (d && typeof d === 'object' ? d.msg || JSON.stringify(d) : String(d)))
			.filter(Boolean)
			.join('; ');
	}
	const code = detail && typeof detail === 'object' ? detail.code : undefined;
	if (typeof code === 'string') {
		const key = `apiError.${code}`;
		const localized = t(key);
		if (localized !== key) return localized;
		return detail.message || key;
	}
	if (detail && typeof detail === 'object') return detail.msg || JSON.stringify(detail);
	return detail;
}

const client = createHttpClient({
	baseUrl: '/api',
	credentials: 'include',
	parseError: (status, body) => {
		const detail = body && typeof body === 'object' ? /** @type {any} */ (body).detail : body;
		const message = detailMessage(detail);
		return message ? String(message) : t('error.http', { status });
	}
});

/** @param {string} p @returns {Promise<any>} */
export const get = (p) => client.get(p);
/** @param {string} p @param {any} [data] @returns {Promise<any>} */
export const post = (p, data) => client.post(p, data);
/** @param {string} p @param {any} [data] @returns {Promise<any>} */
export const put = (p, data) => client.put(p, data);
/** @param {string} p @param {any} [data] @returns {Promise<any>} */
export const patch = (p, data) => client.patch(p, data);
/** @param {string} p @returns {Promise<any>} */
export const del = (p) => client.del(p);

export { errorMessage, errorStatus };
