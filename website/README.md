# dbt-forge website

Public site and docs for `dbt-forge`, built with Astro and Starlight.

Copy and content guidelines live in [`EDITORIAL_GUIDE.md`](./EDITORIAL_GUIDE.md).

## Commands

```bash
pnpm install
pnpm dev
pnpm build
pnpm preview
```

## Vercel

Configure the Vercel project with:

- Root Directory: `website`
- Build Command: `pnpm build`
- Output Directory: `dist`

Preview deployments are expected to come from the Vercel GitHub integration rather than a custom GitHub Actions deploy step.
