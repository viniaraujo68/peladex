<script>
	import { page } from '$app/state';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { dayTypeQuery } from '$lib/dayType.js';
	import { readIdListParam, replaceParams, sidesParams } from '$lib/groupView.svelte.js';
	import { errorMessage, get, post } from '$lib/http.js';
	import { t } from '$lib/i18n.svelte.js';
	import { periodQuery } from '$lib/publicApi.js';
	import PairLeaderboard from './PairLeaderboard.svelte';
	import PlayerCompare from './PlayerCompare.svelte';
	import RivalryBoard from './RivalryBoard.svelte';

	/**
	 * @type {{
	 *   root: string,
	 *   access?: string,
	 *   ranking: import('$lib/types.js').PlayerRow[],
	 *   players: { id: number, name: string }[],
	 *   period: { from: string, to: string },
	 *   dayType: import('$lib/dayType.js').DayType|null,
	 *   playerHref: (playerId: number) => string,
	 *   before?: import('svelte').Snippet
	 * }}
	 */
	let { root, access = '', ranking, players, period, dayType, playerHref, before } = $props();

	const DEFAULT_MIN_DAYS = 3;

	let top = $state(/** @type {HTMLElement|undefined} */ (undefined));
	let pairs = $state(/** @type {import('$lib/types.js').PairLeaderboard|null} */ (null));
	let rivalries = $state(/** @type {import('$lib/types.js').RivalryBoard|null} */ (null));

	const a = $derived(readIdListParam(page.url.searchParams, 'a'));
	const b = $derived(readIdListParam(page.url.searchParams, 'b'));
	const minDays = $derived(Number(page.url.searchParams.get('min_days')) || DEFAULT_MIN_DAYS);

	const accessSuffix = $derived(access ? `?${access}` : '');
	const boardQuery = $derived(
		[access, periodQuery(period), dayTypeQuery(dayType), `min_days=${minDays}`]
			.filter(Boolean)
			.join('&')
	);

	$effect(() => {
		const query = boardQuery;
		let current = true;
		Promise.all([get(`${root}/pairs?${query}`), get(`${root}/rivalries?${query}`)])
			.then(([p, r]) => {
				if (current) [pairs, rivalries] = [p, r];
			})
			.catch((e) => {
				if (current) toast.error(t('group.refreshFailed', { message: errorMessage(e) }));
			});
		return () => {
			current = false;
		};
	});

	/** @param {import('$lib/types.js').ComboRequest} body */
	const runCombo = (body) => post(`${root}/combo${accessSuffix}`, { ...body, day_type: dayType });

	/** @param {number} value */
	const setMinDays = (value) =>
		replaceParams({ min_days: value === DEFAULT_MIN_DAYS ? null : String(value) });

	/** @param {{ a: number[], b: number[] }} sides */
	const setSides = (sides) => replaceParams(sidesParams(sides));

	/** @param {{ a: number[], b: number[] }} sides */
	async function show(sides) {
		await setSides(sides);
		top?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
</script>

<div class="flex flex-col gap-4">
	{@render before?.()}
	<div bind:this={top} class="anchor">
		<PlayerCompare {ranking} {players} {a} {b} {period} onPick={setSides} {runCombo} {playerHref} />
	</div>
	{#if pairs}
		<PairLeaderboard board={pairs} onMinDays={setMinDays} {playerHref} onCompare={show} />
	{/if}
	{#if rivalries}
		<RivalryBoard board={rivalries} onMinDays={setMinDays} {playerHref} onCompare={show} />
	{/if}
</div>

<style>
	.anchor {
		scroll-margin-top: 80px;
	}
</style>
