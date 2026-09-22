/** @type {Record<string, string>} */
const PALETTE = {
	branco: '#f2f3f5',
	preto: '#23262b',
	vermelho: '#e0453f',
	azul: '#2f6fe0',
	verde: '#2f9e51',
	amarelo: '#efc033',
	laranja: '#ee7f2c',
	rosa: '#e46aa2',
	roxo: '#8a5cf0',
	lilas: '#b09ce0',
	cinza: '#8b9199',
	marrom: '#8a5a3c',
	bege: '#d8c8a4',
	vinho: '#8c2740',
	celeste: '#5fc4e8',
	dourado: '#d2ac37',
	prata: '#c3c7cc',
	white: '#f2f3f5',
	black: '#23262b',
	red: '#e0453f',
	blue: '#2f6fe0',
	green: '#2f9e51',
	yellow: '#efc033',
	orange: '#ee7f2c',
	pink: '#e46aa2',
	purple: '#8a5cf0',
	lilac: '#b09ce0',
	gray: '#8b9199',
	grey: '#8b9199',
	brown: '#8a5a3c',
	beige: '#d8c8a4',
	maroon: '#8c2740',
	gold: '#d2ac37',
	silver: '#c3c7cc'
};

const FALLBACK = ['#2f6fe0', '#e0453f', '#2f9e51', '#efc033', '#8a5cf0', '#ee7f2c'];

/** @param {string} value */
function strip(value) {
	return value
		.normalize('NFKD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.trim();
}

/**
 * @param {string} name
 * @param {string} [explicit]
 * @returns {string}
 */
export function teamColor(name, explicit = '') {
	if (explicit) return explicit;
	const key = strip(name ?? '');
	if (PALETTE[key]) return PALETTE[key];
	for (const word of key.split(/\s+/)) {
		if (PALETTE[word]) return PALETTE[word];
	}
	let hash = 0;
	for (let i = 0; i < key.length; i += 1) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
	return FALLBACK[hash % FALLBACK.length];
}
