<script>
	/** @type {{ class?: string, detail?: string, label?: string }} */
	let { class: className = 'size-[1em]', detail = 'var(--color-primary)', label } = $props();
</script>

<svg
	class={className}
	viewBox="0 0 32 32"
	fill="currentColor"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<circle cx="16" cy="16" r="13.2" />
	<path d="M16 6.2l5.1 3.7-1.95 6h-6.3l-1.95-6z" fill={detail} />
	<path d="M7.4 12.6l2.6 8-3.5 2.4A11 11 0 0 1 4.6 16a11 11 0 0 1 .7-3.9z" fill={detail} />
	<path d="M24.6 12.6l2.1 -.5A11 11 0 0 1 27.4 16a11 11 0 0 1-1.9 7l-3.5-2.4z" fill={detail} />
	<path d="M11.6 22.6h8.8l1.5 2.5A11 11 0 0 1 16 27.2a11 11 0 0 1-5.9-1.7z" fill={detail} />
</svg>
