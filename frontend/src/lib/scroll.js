const PANEL_OFFSET = 80;

/** @param {HTMLElement} node */
export function scrollParent(node) {
	let element = node.parentElement;
	while (element) {
		const { overflowY } = getComputedStyle(element);
		const scrollable = overflowY === 'auto' || overflowY === 'scroll';
		if (scrollable && element.scrollHeight > element.clientHeight) return element;
		element = element.parentElement;
	}
	return document.scrollingElement ?? document.documentElement;
}

/** @param {HTMLElement} panel */
export function revealPanelStart(panel) {
	if (panel.getBoundingClientRect().top < PANEL_OFFSET) panel.scrollIntoView({ block: 'start' });
}
