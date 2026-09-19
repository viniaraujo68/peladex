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
