<script>
	import { tick } from 'svelte';

	/**
	 * @type {{
	 *   tabs: Array<{ id: string, label: string }>,
	 *   active: string,
	 *   onChange: (id: string) => void,
	 *   label: string,
	 *   controls: string,
	 *   idPrefix?: string,
	 *   center?: boolean
	 * }}
	 */
	let { tabs, active, onChange, label, controls, idPrefix = 'tab', center = false } = $props();

	/** @param {string} id */
	const tabId = (id) => `${idPrefix}-${id}`;

	/** @param {KeyboardEvent} e */
	function onKey(e) {
		const ids = tabs.map((x) => x.id);
		const from = ids.indexOf(active);
		let to = null;
		if (e.key === 'ArrowRight') to = (from + 1) % ids.length;
		else if (e.key === 'ArrowLeft') to = (from - 1 + ids.length) % ids.length;
		else if (e.key === 'Home') to = 0;
		else if (e.key === 'End') to = ids.length - 1;
		if (to === null) return;
		e.preventDefault();
		const id = ids[to];
		onChange(id);
		tick().then(() => document.getElementById(tabId(id))?.focus());
	}

	/** @type {HTMLElement|undefined} */
	let tabsEl = $state();
	let fadeRight = $state(false);

	function updateFade() {
		if (!tabsEl) return;
		fadeRight = tabsEl.scrollWidth - tabsEl.clientWidth - tabsEl.scrollLeft > 4;
	}

	$effect(() => {
		tabs;
		tabsEl;
		updateFade();
	});
</script>

<div class="tabsbar" class:fade={fadeRight}>
	<div
		class="tabs tabs-border strip"
		class:center
		role="tablist"
		aria-label={label}
		bind:this={tabsEl}
		onscroll={updateFade}
	>
		{#each tabs as item (item.id)}
			<button
				class="tab"
				role="tab"
				id={tabId(item.id)}
				aria-selected={active === item.id}
				aria-controls={controls}
				tabindex={active === item.id ? 0 : -1}
				onclick={() => onChange(item.id)}
				onkeydown={onKey}
			>
				{item.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.tabsbar {
		position: relative;
		margin-bottom: 24px;
	}
	.strip {
		flex-wrap: nowrap;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: none;
		-ms-overflow-style: none;
	}
	.strip.center {
		justify-content: center;
		justify-content: safe center;
	}
	.strip::-webkit-scrollbar {
		display: none;
	}
	.tabsbar.fade .strip {
		-webkit-mask-image: linear-gradient(to right, #000 calc(100% - 44px), transparent);
		mask-image: linear-gradient(to right, #000 calc(100% - 44px), transparent);
	}
	.strip .tab {
		min-height: 44px;
		flex: 0 0 auto;
		white-space: nowrap;
	}
	.strip .tab:focus-visible {
		outline-offset: -2px;
	}
	.strip .tab[aria-selected='true'] {
		color: var(--color-base-content);
		font-weight: 600;
	}
	.strip .tab:not([aria-selected='true']) {
		color: var(--ink-muted);
	}
	.strip .tab:not([aria-selected='true']):hover {
		color: var(--color-base-content);
	}
</style>
