<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Skeleton } from '@viniaraujo68/plinth/components';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { get, post, put, errorMessage } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';
	import MatchdayForm from '$lib/components/MatchdayForm.svelte';

	const groupId = $derived(/** @type {string} */ ($page.params.id));
	const editId = $derived($page.url.searchParams.get('edit'));
	const editing = $derived(!!editId);

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let players = $state(/** @type {import('$lib/types.js').Player[]} */ ([]));
	let venues = $state(/** @type {import('$lib/types.js').Named[]} */ ([]));
	let matchday = $state(/** @type {import('$lib/types.js').Matchday|null} */ (null));
	let lastMatchday = $state(/** @type {import('$lib/types.js').Matchday|null} */ (null));
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) load();
	});

	async function load() {
		loading = true;
		error = '';
		try {
			const [g, p, v, list] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/players`),
				get(`/groups/${groupId}/venues`),
				get(`/groups/${groupId}/matchdays`)
			]);
			group = g;
			players = p;
			venues = v;
			if (editId) {
				matchday = await get(`/groups/${groupId}/matchdays/${editId}`);
				lastMatchday = null;
			} else {
				matchday = null;
				lastMatchday = list[0] ?? null;
			}
		} catch (e) {
			error = t('day.loadFailed', { message: errorMessage(e) });
		} finally {
			loading = false;
		}
	}

	/** @param {import('$lib/types.js').MatchdayPayload} payload */
	async function submit(payload) {
		saving = true;
		try {
			if (editing) await put(`/groups/${groupId}/matchdays/${editId}`, payload);
			else await post(`/groups/${groupId}/matchdays`, payload);
		} catch (e) {
			toast.error(errorMessage(e));
			saving = false;
			return false;
		}
		toast.success(t('toast.matchdaySaved'));
		await goto(`/groups/${groupId}`);
		return true;
	}

	function cancel() {
		goto(`/groups/${groupId}`);
	}
</script>

<svelte:head>
	<title>
		{editing
			? t('title.editMatchday')
			: group
				? t('title.newMatchdayIn', { group: group.name })
				: t('title.newMatchday')}
	</title>
</svelte:head>

<div class="head mb-5">
	<a
		href={`/groups/${groupId}`}
		class="mb-2 inline-block text-sm text-base-content/80 hover:text-base-content"
	>
		{t('day.backToGroup')}
	</a>
	<h1 class="text-2xl font-semibold tracking-tight">
		{editing ? t('day.edit') : t('day.new')}
	</h1>
	{#if group}<p class="mt-1 text-base-content/80">{group.name}</p>{/if}
</div>

{#if loading}
	<div class="flex flex-col gap-4" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		{#each [0, 1, 2] as i (i)}
			<div class="card flex flex-col gap-3 bg-base-100 p-5">
				<Skeleton class="h-3 w-[120px]" />
				<Skeleton class="h-10 w-full" />
				<Skeleton class="h-10 w-3/4" />
			</div>
		{/each}
	</div>
{:else if error}
	<div class="alert alert-soft alert-error">{error}</div>
	<a href={`/groups/${groupId}`} class="btn mt-4">{t('day.backToGroup')}</a>
{:else}
	<MatchdayForm
		{groupId}
		catalogs={{ players, venues }}
		{matchday}
		{lastMatchday}
		{editing}
		{saving}
		onsubmit={submit}
		oncancel={cancel}
	/>
{/if}
