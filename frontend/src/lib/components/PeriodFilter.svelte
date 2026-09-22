<script>
	import { t } from '$lib/i18n.svelte.js';
	import { formatShortDate } from '$lib/format.svelte.js';

	/**
	 * @type {{
	 *   from: string,
	 *   to: string,
	 *   onchange: (range: { from: string, to: string }) => void
	 * }}
	 */
	let { from, to, onchange } = $props();

	let custom = $state(false);
	let rangeError = $state(false);

	/** @param {number} months */
	function monthsAgo(months) {
		const now = new Date();
		const targetMonth = now.getMonth() - months;
		const lastDayOfTargetMonth = new Date(now.getFullYear(), targetMonth + 1, 0).getDate();
		const day = Math.min(now.getDate(), lastDayOfTargetMonth);
		const then = new Date(now.getFullYear(), targetMonth, day);
		return `${then.getFullYear()}-${String(then.getMonth() + 1).padStart(2, '0')}-${String(
			then.getDate()
		).padStart(2, '0')}`;
	}

	/** @param {string} value */
	function isPlausibleDate(value) {
		if (!value) return true;
		const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
		if (!match) return false;
		if (Number(match[1]) < 2000) return false;
		return !Number.isNaN(new Date(value).getTime());
	}

	/** @param {string} newFrom @param {string} newTo */
	function applyRange(newFrom, newTo) {
		if (!isPlausibleDate(newFrom) || !isPlausibleDate(newTo)) return;
		if (newFrom && newTo && newFrom > newTo) {
			rangeError = true;
			return;
		}
		rangeError = false;
		onchange({ from: newFrom, to: newTo });
	}

	const presets = $derived([
		{ id: 'all', label: t('stats.periodAll'), from: '' },
		{ id: '3m', label: t('stats.period3m'), from: monthsAgo(3) },
		{ id: '6m', label: t('stats.period6m'), from: monthsAgo(6) },
		{ id: '12m', label: t('stats.periodYear'), from: monthsAgo(12) }
	]);

	const activePreset = $derived.by(() => {
		if (custom || to) return null;
		return presets.find((p) => p.from === from)?.id ?? null;
	});

	/** @param {{ from: string }} preset */
	function pick(preset) {
		custom = false;
		rangeError = false;
		onchange({ from: preset.from, to: '' });
	}
</script>

<div class="period">
	<span class="plabel">{t('stats.period')}</span>
	<div class="chips" role="group" aria-label={t('stats.period')}>
		{#each presets as preset (preset.id)}
			<button
				type="button"
				class="pchip"
				class:sel={activePreset === preset.id}
				aria-pressed={activePreset === preset.id}
				onclick={() => pick(preset)}
			>
				{preset.label}
			</button>
		{/each}
		<button
			type="button"
			class="pchip"
			class:sel={custom || (activePreset === null && (from || to))}
			aria-pressed={custom}
			onclick={() => (custom = !custom)}
		>
			{t('stats.periodCustom')}
		</button>
	</div>

	{#if custom}
		<div class="period-range">
			<label class="rl">
				<span>{t('filters.from')}</span>
				<input
					class="input input-sm"
					type="date"
					value={from}
					max={to || undefined}
					onchange={(e) => applyRange(e.currentTarget.value, to)}
				/>
			</label>
			<label class="rl">
				<span>{t('filters.to')}</span>
				<input
					class="input input-sm"
					type="date"
					value={to}
					min={from || undefined}
					onchange={(e) => applyRange(from, e.currentTarget.value)}
				/>
			</label>
			{#if from || to}
				<button
					type="button"
					class="btn btn-ghost btn-xs"
					onclick={() => {
						rangeError = false;
						onchange({ from: '', to: '' });
					}}
				>
					{t('import.clear')}
				</button>
			{/if}
		</div>
		{#if rangeError}
			<span class="rangeerror">{t('filters.invalidRange')}</span>
		{/if}
	{:else if from || to}
		<span class="rangetext">
			{t('stats.periodRange', {
				from: from ? formatShortDate(from) : '…',
				to: to ? formatShortDate(to) : '…'
			})}
		</span>
	{/if}
</div>

<style>
	.period {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px;
	}
	.plabel {
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-muted);
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.pchip {
		min-height: 32px;
		padding: 4px 11px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		background: var(--color-base-100);
		color: var(--ink-muted);
		font-size: 0.78rem;
		cursor: pointer;
	}
	.pchip:hover {
		color: var(--color-base-content);
	}
	.pchip.sel {
		border-color: var(--color-primary);
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
		font-weight: 600;
	}
	.period-range {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 8px;
	}
	.rl {
		display: flex;
		flex-direction: column;
		gap: 3px;
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-muted);
	}
	.rangetext {
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.rangeerror {
		font-size: 0.72rem;
		color: var(--color-error);
	}
	@media (max-width: 560px) {
		.pchip {
			min-height: 40px;
		}
	}
</style>
