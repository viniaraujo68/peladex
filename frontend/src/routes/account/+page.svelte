<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { auth, changePassword, logoutEverywhere } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { loginUrl } from '$lib/nav.js';
	import { t } from '$lib/i18n.svelte.js';

	let current = $state('');
	let next = $state('');
	let confirmation = $state('');
	let busy = $state(false);
	let error = $state('');

	const mismatch = $derived(confirmation.length > 0 && next !== confirmation);
	const tooShort = $derived(next.length > 0 && next.length < 6);

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		if (mismatch || tooShort) return;
		busy = true;
		error = '';
		try {
			await changePassword(current, next);
			toast.success(t('account.passwordChanged'));
			current = '';
			next = '';
			confirmation = '';
		} catch (e) {
			error = errorMessage(e);
		} finally {
			busy = false;
		}
	}

	async function signOutEverywhere() {
		await logoutEverywhere();
		await goto('/');
	}
</script>

<svelte:head><title>{t('title.account')}</title></svelte:head>

{#if auth.user}
	<div class="mx-auto flex max-w-[520px] flex-col gap-4">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">{t('account.title')}</h1>
			<p class="mt-1 text-base-content/80">
				{t('account.subtitle', { name: auth.user.username })}
			</p>
		</div>

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<h2 class="font-semibold">{t('account.changePassword')}</h2>
			{#if error}<div class="alert alert-soft alert-error">{error}</div>{/if}
			<form class="flex flex-col gap-3" onsubmit={submit}>
				<div class="flex flex-col gap-1.5">
					<label class="text-xs font-medium text-base-content/80" for="cp">
						{t('account.currentPassword')}
					</label>
					<input
						id="cp"
						class="input w-full"
						type="password"
						bind:value={current}
						autocomplete="current-password"
						required
					/>
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-xs font-medium text-base-content/80" for="np">
						{t('account.newPassword')}
					</label>
					<input
						id="np"
						class="input w-full"
						type="password"
						bind:value={next}
						autocomplete="new-password"
						required
					/>
					{#if tooShort}
						<span class="text-xs text-error">{t('auth.passwordTooShort')}</span>
					{/if}
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-xs font-medium text-base-content/80" for="cf">
						{t('account.confirmPassword')}
					</label>
					<input
						id="cf"
						class="input w-full"
						type="password"
						bind:value={confirmation}
						autocomplete="new-password"
						required
					/>
					{#if mismatch}
						<span class="text-xs text-error">{t('account.passwordMismatch')}</span>
					{/if}
				</div>
				<button
					class="btn btn-primary self-start"
					disabled={busy || !current || next.length < 6 || mismatch}
				>
					{busy ? t('common.saving') : t('common.save')}
				</button>
			</form>
		</section>

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			<h2 class="font-semibold">{t('account.sessions')}</h2>
			<p class="text-sm text-base-content/65">{t('account.logoutAllHint')}</p>
			<button class="btn btn-soft btn-error self-start" onclick={signOutEverywhere}>
				{t('account.logoutAll')}
			</button>
		</section>
	</div>
{/if}
