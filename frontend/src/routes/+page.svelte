<script>
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { Modal, Skeleton } from '@viniaraujo68/plinth/components';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { get, post, errorMessage } from '$lib/http.js';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { t } from '$lib/i18n.svelte.js';

	const title = $derived(auth.ready && auth.user ? t('title.myGroups') : t('title.home'));

	let groups = $state(/** @type {import('$lib/types.js').Group[]} */ ([]));
	let loading = $state(true);
	let error = $state('');
	let query = $state('');

	const filteredGroups = $derived(
		query.trim()
			? groups.filter((g) => g.name.toLowerCase().includes(query.trim().toLowerCase()))
			: groups
	);

	let createModal = $state(
		/** @type {import('@viniaraujo68/plinth/components').Modal|undefined} */ (undefined)
	);
	let name = $state('');
	let description = $state('');
	let visibility = $state('public');
	let creating = $state(false);
	let createError = $state('');

	const VISIBILITIES = ['public', 'private'];
	/** @param {KeyboardEvent} e */
	function onVisKey(e) {
		if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(e.key)) return;
		e.preventDefault();
		visibility = VISIBILITIES[(VISIBILITIES.indexOf(visibility) + 1) % VISIBILITIES.length];
		tick().then(() => document.getElementById(`vis-${visibility}`)?.focus());
	}

	$effect(() => {
		if (auth.ready) {
			if (auth.user) loadGroups();
			else loading = false;
		}
	});

	async function loadGroups() {
		loading = true;
		try {
			groups = await get('/groups');
		} catch (e) {
			error = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/** @param {SubmitEvent} ev */
	async function createGroup(ev) {
		ev.preventDefault();
		creating = true;
		createError = '';
		try {
			const g = await post('/groups', { name, description, visibility });
			goto(`/groups/${g.id}`);
		} catch (e) {
			createError = errorMessage(e);
			creating = false;
		}
	}
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={t('home.tagline')} />
</svelte:head>

{#if !auth.ready || loading}
	<div class="flex flex-col gap-2.5" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<Skeleton class="h-[30px] w-[min(240px,60%)]" />
		<Skeleton class="mb-3.5 h-3 w-[min(160px,45%)]" />
		<div class="groups grid gap-4">
			{#each [0, 1, 2] as i (i)}
				<div class="card flex flex-col gap-3 bg-base-100 p-5">
					<Skeleton class="h-[18px] w-3/5" />
					<Skeleton class="h-3 w-[85%]" />
					<div class="mt-auto flex gap-2">
						<Skeleton class="h-[22px] w-[84px]" rounded="full" />
						<Skeleton class="h-[22px] w-[84px]" rounded="full" />
					</div>
				</div>
			{/each}
		</div>
	</div>
{:else if !auth.user}
	<section class="hero">
		<span class="logo-big"><BrandMark /></span>
		<h1 class="hero-title">Peladex</h1>
		<p class="text-lg text-base-content/80">{t('home.tagline')}</p>
		<div class="mt-2.5 flex items-center gap-3">
			<a href="/register" class="btn btn-primary">{t('nav.register')}</a>
			<a href="/login" class="btn">{t('nav.login')}</a>
		</div>
	</section>
{:else}
	<div class="head flex items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">{t('home.myGroups')}</h1>
			<p class="mt-1 text-base-content/80">{t('home.greeting', { name: auth.user.username })}</p>
		</div>
		<button class="btn btn-primary" onclick={() => createModal?.show()}>
			{t('home.newGroup')}
		</button>
	</div>

	{#if error}<div class="alert alert-soft alert-error">{error}</div>{/if}

	<Modal
		bind:this={createModal}
		title={t('group.create')}
		closeLabel={t('common.close')}
		class="max-w-[460px]"
	>
		<form id="create-group" class="flex flex-col gap-4" onsubmit={createGroup}>
			{#if createError}<div class="alert alert-soft alert-error">{createError}</div>{/if}
			<div class="flex flex-col gap-1.5">
				<label class="text-xs font-medium text-base-content/80" for="g-name">
					{t('group.nameLabel')}
				</label>
				<!-- svelte-ignore a11y_autofocus -->
				<input id="g-name" class="input w-full" bind:value={name} autofocus required />
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="text-xs font-medium text-base-content/80" for="g-desc">
					{t('common.description')}
					<span class="font-normal text-base-content/65">{t('common.optional')}</span>
				</label>
				<input id="g-desc" class="input w-full" bind:value={description} />
			</div>
			<div class="flex flex-col gap-1.5">
				<span class="text-xs font-medium text-base-content/80" id="vis-label">
					{t('group.visibility')}
				</span>
				<div class="vis" role="radiogroup" aria-labelledby="vis-label">
					<button
						type="button"
						id="vis-public"
						class="vis-opt"
						class:sel={visibility === 'public'}
						role="radio"
						aria-checked={visibility === 'public'}
						tabindex={visibility === 'public' ? 0 : -1}
						onkeydown={onVisKey}
						onclick={() => (visibility = 'public')}
					>
						<Icon name="globe" class="size-5" />
						<span class="font-semibold">{t('group.public')}</span>
						<span class="vis-d text-base-content/65">{t('group.publicHint')}</span>
					</button>
					<button
						type="button"
						id="vis-private"
						class="vis-opt"
						class:sel={visibility === 'private'}
						role="radio"
						aria-checked={visibility === 'private'}
						tabindex={visibility === 'private' ? 0 : -1}
						onkeydown={onVisKey}
						onclick={() => (visibility = 'private')}
					>
						<Icon name="lock" class="size-5" />
						<span class="font-semibold">{t('group.private')}</span>
						<span class="vis-d text-base-content/65">{t('group.privateHint')}</span>
					</button>
				</div>
			</div>
		</form>

		{#snippet footer()}
			<button type="button" class="btn" onclick={() => createModal?.close()}>
				{t('common.cancel')}
			</button>
			<button class="btn btn-primary" form="create-group" disabled={creating || !name}>
				{creating ? t('group.creating') : t('group.create')}
			</button>
		{/snippet}
	</Modal>

	{#if groups.length === 0}
		<div class="card items-center gap-4 bg-base-100 px-5 py-12 text-center">
			<p class="text-base-content/65">{t('home.empty')}</p>
			<button class="btn btn-primary" onclick={() => createModal?.show()}>
				{t('home.newGroup')}
			</button>
		</div>
	{:else}
		{#if groups.length > 3}
			<label class="input search-field mb-4.5 w-full">
				<Icon name="search" class="size-4 opacity-55" />
				<input placeholder={t('home.searchPlaceholder')} bind:value={query} />
			</label>
		{/if}
		{#if filteredGroups.length === 0}
			<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
				{t('home.noResults', { query })}
			</div>
		{:else}
			<div class="groups grid gap-4">
				{#each filteredGroups as g (g.id)}
					<GroupCard group={g} href={`/groups/${g.id}`} visibility={g.visibility} />
				{/each}
			</div>
		{/if}
	{/if}
{/if}

<style>
	.hero {
		position: relative;
		isolation: isolate;
		text-align: center;
		max-width: 560px;
		margin: 10vh auto 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
	}
	.hero::before {
		content: '';
		position: absolute;
		inset: -16vh -26% auto;
		height: 42vh;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(
				48% 52% at 50% 42%,
				color-mix(in oklch, var(--color-primary) 20%, transparent),
				transparent 72%
			),
			radial-gradient(
				34% 34% at 72% 74%,
				color-mix(in oklch, var(--color-warning) 11%, transparent),
				transparent 72%
			);
	}
	.logo-big {
		display: grid;
		place-items: center;
		width: 72px;
		height: 72px;
		border-radius: var(--radius-box);
		background-color: var(--color-primary);
		color: var(--color-primary-content);
		font-size: 3.1rem;
		box-shadow: 0 18px 40px -18px color-mix(in oklch, var(--color-primary) 70%, transparent);
	}
	.hero-title {
		font-size: clamp(2.2rem, 6vw, 3rem);
		font-weight: 600;
		letter-spacing: -0.03em;
		line-height: 1.1;
	}
	.head {
		margin-bottom: 24px;
	}
	@media (max-width: 560px) {
		.head {
			flex-direction: column;
			align-items: stretch;
			gap: 12px;
		}
		.head :global(.btn) {
			width: 100%;
		}
		.search-field {
			max-width: none;
		}
	}
	.vis {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	@media (max-width: 560px) {
		.vis {
			grid-template-columns: 1fr;
		}
	}
	.vis-opt {
		display: flex;
		flex-direction: column;
		gap: 3px;
		text-align: left;
		padding: 12px 14px;
		border-radius: var(--radius-field);
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		background: var(--color-base-100);
		color: var(--color-base-content);
		cursor: pointer;
	}
	.vis-opt:hover {
		border-color: color-mix(in oklch, var(--color-primary) 55%, transparent);
	}
	.vis-opt.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 12%, transparent);
	}
	.vis-opt :global(svg) {
		margin-bottom: 2px;
		color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
	}
	.vis-opt.sel :global(svg) {
		color: var(--ink-primary);
	}
	.vis-d {
		font-size: 0.74rem;
		line-height: 1.3;
	}
	.search-field {
		max-width: 360px;
	}
	.groups {
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	}
</style>
