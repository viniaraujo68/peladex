<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { auth, register } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { safeNext, withNext } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';

	let username = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state('');

	const next = $derived(safeNext($page.url.searchParams.get('next')));
	const tooShort = $derived(password.length > 0 && password.length < 6);

	$effect(() => {
		if (auth.ready && auth.user) goto(next ?? '/');
	});

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		if (tooShort) return;
		busy = true;
		error = '';
		try {
			await register(username, password);
			await goto(next ?? '/');
		} catch (e) {
			error = errorMessage(e);
			busy = false;
		}
	}
</script>

<svelte:head><title>{t('title.register')}</title></svelte:head>

<div class="authbox card mx-auto mt-[6vh] max-w-[400px] gap-4 bg-base-100 p-6">
	<div>
		<h1 class="text-xl font-semibold tracking-tight">{t('auth.register')}</h1>
		<p class="mt-1 text-sm text-base-content/80">{t('auth.registerSubtitle')}</p>
	</div>

	{#if error}<div class="alert alert-soft alert-error">{error}</div>{/if}

	<form class="flex flex-col gap-3" onsubmit={submit}>
		<div class="flex flex-col gap-1.5">
			<label class="text-xs font-medium text-base-content/80" for="u">{t('auth.username')}</label>
			<input id="u" class="input w-full" bind:value={username} autocomplete="username" required />
		</div>
		<div class="flex flex-col gap-1.5">
			<label class="text-xs font-medium text-base-content/80" for="p">{t('auth.password')}</label>
			<input
				id="p"
				class="input w-full"
				type="password"
				bind:value={password}
				autocomplete="new-password"
				required
			/>
			{#if tooShort}
				<span class="text-xs text-error">{t('auth.passwordTooShort')}</span>
			{/if}
		</div>
		<button class="btn btn-primary mt-1" disabled={busy || !username || password.length < 6}>
			{busy ? t('auth.registering') : t('auth.register')}
		</button>
	</form>

	<p class="text-center text-sm text-base-content/80">
		{t('auth.hasAccount')}
		<a class="link-primary" href={withNext('/login', next)}>{t('auth.login')}</a>
	</p>
</div>
