/**
 * @param {string|null|undefined} value
 * @returns {string|null}
 */
export function safeNext(value) {
	if (typeof value !== 'string') return null;
	if (!value.startsWith('/')) return null;
	if (value.startsWith('//') || value.startsWith('/\\')) return null;
	return value;
}

/** @param {URL} url */
export function loginUrl(url) {
	const path = url?.pathname ?? '/';
	return path === '/' ? '/login' : `/login?next=${encodeURIComponent(path)}`;
}

/**
 * @param {string} base
 * @param {string|null} next
 */
export function withNext(base, next) {
	return next ? `${base}?next=${encodeURIComponent(next)}` : base;
}
