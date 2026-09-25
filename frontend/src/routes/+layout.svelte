<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { navigating } from '$app/stores';
	import { page } from '$app/state';
	import { RoutingContext, setRoutingContext } from '@viniaraujo68/plinth/routing';
	import { AppShell } from '@viniaraujo68/plinth/shell';
	import {
		readThemePreference,
		setThemeContext,
		ThemeContext,
		ThemeController,
		ThemeToggle
	} from '@viniaraujo68/plinth/theme';
	import { setUserContext } from '@viniaraujo68/plinth/user';
	import { Toaster } from '@viniaraujo68/plinth/toast';
	import { Confirmer } from '@viniaraujo68/plinth/confirm';
	import { routes } from '$lib/routes.js';
	import { user } from '$lib/user.js';
	import { auth, loadUser } from '$lib/stores/auth.svelte.js';
	import { i18n, setLocale, t } from '$lib/i18n.svelte.js';
	import BrandMark from '$lib/components/BrandMark.svelte';

	let { children } = $props();

	setRoutingContext(new RoutingContext(routes, page));
	setUserContext(user);
	setThemeContext(new ThemeContext(browser ? readThemePreference() : 'system'));

	onMount(loadUser);

	const isPublic = $derived(page.route.id?.startsWith('/g/') ?? false);

	/** @param {import('@viniaraujo68/plinth/theme').ThemePreference} preference */
	const themePreferenceLabel = (preference) => t(`theme.${preference}`);

	/**
	 * @param {import('@viniaraujo68/plinth/theme').ThemePreference} current
	 * @param {import('@viniaraujo68/plinth/theme').ThemePreference} next
	 */
	const themeLabel = (current, next) =>
		t('theme.switchTo', {
			current: themePreferenceLabel(current),
			next: themePreferenceLabel(next)
		});

	const GRACE_MS = 150;
	let showProgress = $state(false);

	$effect(() => {
		if (!$navigating) {
			showProgress = false;
			return;
		}
		const timer = setTimeout(() => (showProgress = true), GRACE_MS);
		return () => clearTimeout(timer);
	});
</script>

<ThemeController />

{#if showProgress}
	<div class="navbar-progress" aria-hidden="true"><span></span></div>
{/if}

{#snippet brandMark(collapsed = false)}
	<a href="/" class="brand">
		<span class="logo"><BrandMark label={collapsed ? 'Peladex' : undefined} /></span>
		{#if !collapsed}<span class="brand-name">Peladex</span>{/if}
	</a>
{/snippet}

{#snippet langToggle()}
	<div class="lang" role="group" aria-label={t('nav.language')}>
		<button
			class="lang-opt"
			class:sel={i18n.locale === 'pt'}
			aria-pressed={i18n.locale === 'pt'}
			title={t('nav.switchToPt')}
			onclick={() => setLocale('pt')}>PT</button
		>
		<button
			class="lang-opt"
			class:sel={i18n.locale === 'en'}
			aria-pressed={i18n.locale === 'en'}
			title={t('nav.switchToEn')}
			onclick={() => setLocale('en')}>EN</button
		>
	</div>
{/snippet}

{#if isPublic}
	<header class="public-nav">
		<div class="container public-nav-inner">
			{@render brandMark()}
			<div class="public-nav-right">
				{#if auth.ready && !auth.user}
					<a href="/register" class="btn btn-sm btn-primary">{t('nav.register')}</a>
				{/if}
				{@render langToggle()}
				<ThemeToggle iconOnly preferenceLabel={themePreferenceLabel} label={themeLabel} />
			</div>
		</div>
	</header>

	<main class="container page">
		{@render children()}
	</main>
{:else}
	<div class="shell-host">
		<AppShell
			navLabel={t('nav.main')}
			collapseLabel={t('nav.collapse')}
			moreLabel={t('nav.more')}
			closeLabel={t('common.close')}
			logoutLabel={t('nav.logout')}
		>
			{#snippet brand({ collapsed })}
				{@render brandMark(collapsed)}
			{/snippet}

			{#snippet icon(route)}
				{@const name = route.meta.icon}
				<svg
					class="size-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.75"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					{#if name === 'home'}
						<path d="M3 10.5 12 3l9 7.5" />
						<path d="M5 9.5V21h14V9.5" />
					{:else if name === 'explore'}
						<circle cx="12" cy="12" r="9" />
						<path d="m15.5 8.5-2 5-5 2 2-5z" />
					{:else if name === 'account'}
						<circle cx="12" cy="8" r="3.5" />
						<path d="M5 20a7 7 0 0 1 14 0" />
					{:else if name === 'login'}
						<path d="M10 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4" />
						<path d="m15 8 4 4-4 4M19 12H9" />
					{:else if name === 'register'}
						<circle cx="9" cy="8" r="3.5" />
						<path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
						<path d="M19 8v6M22 11h-6" />
					{/if}
				</svg>
			{/snippet}

			{#snippet footer()}
				<div class="shell-controls">
					{@render langToggle()}
					<ThemeToggle iconOnly preferenceLabel={themePreferenceLabel} label={themeLabel} />
				</div>
			{/snippet}

			<div class="container page">
				{@render children()}
			</div>
		</AppShell>
	</div>
{/if}

<Toaster
	class="z-[80]"
	position="top-end"
	label={t('toast.region')}
	dismissLabel={t('common.close')}
/>

<Confirmer
	confirmLabel={t('common.confirm')}
	cancelLabel={t('common.cancel')}
	closeLabel={t('common.close')}
	challengeLabel={(value) => t('common.typeToConfirm', { value })}
/>

<style>
	.container {
		width: 100%;
		max-width: 1080px;
		margin: 0 auto;
		padding: 0 20px;
	}
	.navbar-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 60;
		height: 2px;
		overflow: hidden;
		background: transparent;
		pointer-events: none;
	}
	.navbar-progress span {
		display: block;
		width: 40%;
		height: 100%;
		border-radius: 0 2px 2px 0;
		background: linear-gradient(90deg, transparent, var(--color-primary));
		animation: navbar-progress-sweep 1.1s ease-in-out infinite;
	}
	@keyframes navbar-progress-sweep {
		from {
			transform: translateX(-100%);
		}
		to {
			transform: translateX(250%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.navbar-progress span {
			width: 100%;
			animation: none !important;
			background: var(--color-primary);
		}
	}
	.shell-host {
		height: 100dvh;
	}
	.public-nav {
		position: sticky;
		top: 0;
		z-index: 50;
		background: color-mix(in oklch, var(--color-base-100) 82%, transparent);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
	}
	.public-nav-inner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 64px;
	}
	.public-nav-right {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	@media (max-width: 560px) {
		.public-nav-right {
			gap: 8px;
		}
	}
	@media (max-width: 400px) {
		.public-nav .brand-name {
			display: none;
		}
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.logo {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: var(--radius-field);
		background-color: var(--color-primary);
		color: var(--color-primary-content);
		font-size: 1.5rem;
		font-weight: 700;
	}
	.brand-name {
		font-weight: 700;
		font-size: 1.15rem;
		letter-spacing: -0.02em;
	}
	.shell-controls {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	:global(.plinth-shell.collapsed .shell-sidebar) .shell-controls {
		flex-direction: column;
	}
	:global(.plinth-sheet) .shell-controls {
		flex-direction: row;
	}
	.lang {
		display: flex;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		overflow: hidden;
		background: var(--color-base-100);
	}
	:global(.plinth-shell.collapsed .shell-sidebar) .lang {
		flex-direction: column;
	}
	:global(.plinth-sheet) .lang {
		flex-direction: row;
	}
	:global(.plinth-sheet) .lang-opt {
		min-height: 2.25rem;
		padding: 6px 14px;
	}
	.lang-opt {
		background: none;
		border: none;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		font-family: inherit;
		font-size: 0.72rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		padding: 6px 9px;
		cursor: pointer;
	}
	.lang-opt:hover:not(.sel) {
		color: var(--color-base-content);
	}
	.lang-opt.sel {
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
	}
	.page {
		padding-top: 32px;
		padding-bottom: 64px;
		overflow-x: clip;
	}
</style>
