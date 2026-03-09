// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://dbt-forge.marou.one',
	integrations: [
		starlight({
			title: 'dbt-forge',
			description: 'Python CLI for scaffolding dbt projects with a consistent starting structure.',
			tagline: 'Scaffold a dbt project with a consistent starting structure.',
			favicon: '/favicon.svg',
			editLink: {
				baseUrl: 'https://github.com/maroil/dbt-forge/edit/main/website/src/content/docs/',
			},
			customCss: ['./src/styles/site.css'],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/maroil/dbt-forge' }],
			sidebar: [
				{
					label: 'Start here',
					items: [
						{ label: 'Docs home', slug: 'docs' },
						{ label: 'Getting started', slug: 'docs/getting-started' },
						{ label: 'Project structure', slug: 'docs/project-structure' },
						{ label: 'Development', slug: 'docs/development' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'dbt project template', slug: 'docs/guides/dbt-project-template' },
						{
							label: 'How to scaffold a dbt project',
							slug: 'docs/guides/how-to-scaffold-a-dbt-project',
						},
						{ label: 'Migrate SQL to dbt', slug: 'docs/guides/migrate-sql-to-dbt' },
						{
							label: 'dbt project best practices',
							slug: 'docs/guides/dbt-project-best-practices',
						},
						{ label: 'dbt Mesh project setup', slug: 'docs/guides/dbt-mesh-project-setup' },
					],
				},
				{
					label: 'CLI reference',
					items: [
						{ label: 'init', slug: 'docs/cli/init' },
						{ label: 'add', slug: 'docs/cli/add' },
						{ label: 'migrate', slug: 'docs/cli/migrate' },
						{ label: 'docs generate', slug: 'docs/cli/docs' },
						{ label: 'doctor', slug: 'docs/cli/doctor' },
						{ label: 'status', slug: 'docs/cli/status' },
						{ label: 'update', slug: 'docs/cli/update' },
						{ label: 'preset', slug: 'docs/cli/preset' },
					],
				},
			],
			credits: false,
		}),
	],
});
