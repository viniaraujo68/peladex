import { t } from '$lib/i18n.svelte.js';

/** @type {import('@viniaraujo68/plinth/routing').RoutingConfig<import('$app/types').RouteId>} */
export const routes = {
	meta: {
		'/': { title: () => t('nav.home'), icon: 'home' },
		'/explore': { title: () => t('nav.explore'), icon: 'explore' },
		'/account': { title: () => t('nav.account'), icon: 'account', requiredRoles: ['user'] },
		'/login': { title: () => t('nav.login'), icon: 'login', requiredRoles: ['guest'] },
		'/register': { title: () => t('nav.register'), icon: 'register', requiredRoles: ['guest'] },

		'/groups/[id]': {},
		'/groups/[id]/matchdays/new': {},
		'/groups/[id]/matchdays/import': {},
		'/groups/[id]/analise': {},
		'/groups/[id]/players/[playerId]': {},
		'/g/[slug]': {},
		'/g/[slug]/players/[playerId]': {},
		'/g/[slug]/analise': {}
	},

	pages: import.meta.glob('/src/routes/**/+page.svelte')
};
