import { loadPublicGroup } from '$lib/publicApi.js';

export const ssr = true;

/** @type {import('./$types').PageLoad} */
export const load = (event) => loadPublicGroup(event);
