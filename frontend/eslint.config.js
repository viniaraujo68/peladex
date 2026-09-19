import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';

export default [
	{
		ignores: ['build/', '.svelte-kit/', 'node_modules/']
	},

	js.configs.recommended,
	...svelte.configs.recommended,

	{
		languageOptions: {
			ecmaVersion: 2023,
			sourceType: 'module',
			globals: { ...globals.browser, ...globals.node }
		},
		rules: {
			'no-empty': ['error', { allowEmptyCatch: true }],
			'svelte/no-navigation-without-resolve': 'off',
			'svelte/prefer-svelte-reactivity': 'off',
			'no-unused-vars': [
				'error',
				{ argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' }
			]
		}
	},

	{
		files: ['*.config.js', 'src/hooks.server.js'],
		languageOptions: { globals: globals.node }
	}
];
