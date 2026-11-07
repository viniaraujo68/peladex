import { t } from './i18n.svelte.js';

export function publicTabs() {
	return [
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'combos', label: t('tab.combos') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'matchdays', label: t('tab.matchdays') }
	];
}

export function ownerTabs() {
	return [
		{ id: 'matchdays', label: t('tab.matchdays') },
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'players', label: t('tab.players') },
		{ id: 'combos', label: t('tab.combos') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'settings', label: t('tab.settings') }
	];
}
