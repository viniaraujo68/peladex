<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { get, post, errorMessage } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import { setTrackingContext } from '$lib/tracking.svelte.js';
	import { withParams } from '$lib/viewState.js';
	import ComboExplorer from '$lib/components/ComboExplorer.svelte';
	import PlayerCompare from '$lib/components/PlayerCompare.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let players = $state(/** @type {import('$lib/types.js').Player[]} */ ([]));
	let stats = $state(/** @type {import('$lib/types.js').Stats|null} */ (null));

	setTrackingContext({
		get trackScorers() {
			return group?.track_scorers ?? true;
		},
		get trackAssists() {
			return group?.track_assists ?? false;
		},
		get showRatings() {
			return group?.show_ratings ?? true;
		}
	});
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) load();
	});

	async function load() {
		loading = true;
		try {
			[group, players, stats] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players`),
				get(`/groups/${groupId}/stats`)
			]);
		} catch (e) {
			error = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/** @param {any} body */
	const run = (body) => post(`/groups/${groupId}/combo`, body);

	/** @param {number} id */
	const loadDetail = (id) => get(`/groups/${groupId}/players/${id}/detail`);

	/** @param {number} playerId */
	const playerHref = (playerId) => `/groups/${groupId}/players/${playerId}`;

	/** @param {string} key */
	const idParam = (key) => {
		const value = Number($page.url.searchParams.get(key));
		return Number.isInteger(value) && value > 0 ? value : null;
	};

	/** @param {{ a: number|null, b: number|null }} pick */
	function setPick(pick) {
		const url = withParams($page.url, {
			a: pick.a === null ? null : String(pick.a),
			b: pick.b === null ? null : String(pick.b)
		});
		goto(url, { keepFocus: true, noScroll: true, replaceState: true });
	}
</script>

<svelte:head><title>{t('analysis.title')} · Peladex</title></svelte:head>

<div class="head mb-5">
	<a
		href={`/groups/${groupId}?tab=players`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('day.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">{t('analysis.title')}</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

{#if loading}
	<div class="flex flex-col gap-4" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<Skeleton class="h-[120px]" />
		<Skeleton class="h-[220px]" />
	</div>
{:else if error}
	<div class="alert alert-soft alert-error">{error}</div>
{:else}
	<div class="flex flex-col gap-8">
		{#if stats}
			<PlayerCompare
				ranking={stats.ranking}
				a={idParam('a')}
				b={idParam('b')}
				onPick={setPick}
				{loadDetail}
				runCombo={run}
				{playerHref}
			/>
		{/if}
		<div class="flex flex-col gap-3">
			<h2 class="font-semibold">{t('analysis.combosTitle')}</h2>
			<ComboExplorer players={players.map((p) => ({ id: p.id, name: p.name }))} {run} />
		</div>
	</div>
{/if}
