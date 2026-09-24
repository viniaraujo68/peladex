import { createCssColorReader } from '@viniaraujo68/plinth/theme';

/** @param {HTMLElement} host */
export function readChartTheme(host) {
	const reader = createCssColorReader(host);
	/** @param {number} percent @param {string} fallback */
	const ink = (percent, fallback) =>
		reader.read(`color-mix(in oklch, var(--color-base-content) ${percent}%, transparent)`, fallback);
	const axis = ink(65, '#857da3');
	const text = ink(85, '#c8cee0');
	const surface = reader.read('var(--color-base-100)', '#ffffff');
	return {
		read: reader.read,
		dispose: reader.dispose,
		ink,
		axis,
		text,
		surface,
		grid: ink(10, 'rgba(127,127,127,0.12)'),
		tooltip: {
			backgroundColor: surface,
			borderColor: ink(14, 'rgba(127,127,127,0.16)'),
			borderWidth: 1,
			titleColor: axis,
			bodyColor: text,
			padding: 10,
			cornerRadius: 8
		}
	};
}
