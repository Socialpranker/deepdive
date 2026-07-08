# GitHub Pages site

This folder is published as a GitHub Pages site at:

```
https://socialpranker.github.io/deepdive/
```

> **Canonical URL.** The site is served from the **`Socialpranker`** account, so the
> only correct host is `socialpranker.github.io`. Any other GitHub Pages host
> (e.g. `ivanterescheenko-ai.github.io`) is **wrong** and returns 404.
>
> The "About → website" link in the GitHub sidebar is the repo's **homepage field**,
> *not* a file in this repo — editing `_config.yml` or `index.html` does **not** change it.
> Fix it in **Settings → General → Website**, or via CLI:
>
> ```
> gh api -X PATCH repos/Socialpranker/deepdive \
>   -f homepage="https://socialpranker.github.io/deepdive/"
> ```

## How to enable

1. Go to repo Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: **main** → Folder: **/docs**
4. Save

After ~1 minute, the site will be live.

## Files

- `index.html` — main landing page
- `_config.yml` — Jekyll config (mostly metadata for SEO)
- `README.md` — this file (excluded from Jekyll build)

## Custom domain (optional)

If you have a domain (e.g., `deep-research-skill.com`):

1. Create `docs/CNAME` with the domain on a single line
2. Configure DNS: CNAME record `yourdomain.com → socialpranker.github.io`
3. Settings → Pages → Custom domain → enter domain → check "Enforce HTTPS"

## Social preview image (og-image)

To customize the social media preview image:

1. Create a 1200×630 PNG image
2. Save as `docs/og-image.png`
3. Already linked in `<meta property="og:image">` in index.html

Quick way: use https://og-image.vercel.app or screenshot the hero section.

## Updating

The page is static HTML — edit `docs/index.html` and push. GitHub Pages rebuilds automatically.

For SEO, update `_config.yml` description after pushing.
