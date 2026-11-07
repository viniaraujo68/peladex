/** @param {string} value */
export function fold(value) {
	return value
		.normalize('NFKD')
		.replace(/[̀-ͯ]/g, '')
		.replace(/\s+/g, ' ')
		.trim()
		.toLowerCase();
}
