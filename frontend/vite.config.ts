import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API lived on Railway until that subscription lapsed. A stale VITE_API_URL
// pointing at the dead host may still be configured in the Vercel dashboard, and
// an injected variable beats .env.production — which would ship a bundle that
// calls a server that no longer exists.
//
// Ignore that one retired host so the build falls back to the committed value.
// Once the variable is removed from the Vercel dashboard this guard is inert and
// the file can go back to a plain defineConfig({ plugins: [react()] }).
const RETIRED_API_HOST = '.up.railway.app'

/**
 * Read VITE_* values from the .env files only.
 *
 * Vite's own `loadEnv` helper cannot be used here: it merges `process.env` over
 * the file values for prefixed keys, so it would hand back the very injected
 * value this guard needs to override.
 */
function readEnvFiles(dir: string, mode: string): Record<string, string> {
  const out: Record<string, string> = {}
  // Later files win, matching Vite's own precedence.
  for (const name of ['.env', `.env.${mode}`]) {
    const path = resolve(dir, name)
    if (!existsSync(path)) continue
    for (const rawLine of readFileSync(path, 'utf-8').split(/\r?\n/)) {
      const line = rawLine.trim()
      if (!line || line.startsWith('#')) continue
      const eq = line.indexOf('=')
      if (eq === -1) continue
      const key = line.slice(0, eq).trim()
      let value = line.slice(eq + 1).trim()
      const quoted =
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      if (quoted && value.length >= 2) value = value.slice(1, -1)
      out[key] = value
    }
  }
  return out
}

export default defineConfig(({ mode }) => {
  const fromFile = readEnvFiles(process.cwd(), mode).VITE_API_URL
  const injected = process.env.VITE_API_URL // set by Vercel / Docker build arg

  // Note: an explicit empty string is meaningful — the Docker/nginx image passes
  // VITE_API_URL="" so all /api/* calls stay relative to the same origin.
  // `??` preserves that; `||` would not.
  let resolved: string | undefined = injected ?? fromFile

  if (resolved !== undefined && resolved.includes(RETIRED_API_HOST)) {
    const replacement =
      fromFile !== undefined && !fromFile.includes(RETIRED_API_HOST) ? fromFile : undefined
    console.warn(
      `\n[vite] VITE_API_URL points at the retired host "${resolved}".\n` +
        `       Using ${replacement ? `"${replacement}" from .env.${mode}` : 'the in-app default'} instead.\n` +
        `       Remove VITE_API_URL from the Vercel dashboard to silence this.\n`,
    )
    resolved = replacement
  }

  return {
    plugins: [react()],
    // When nothing resolves, emit no define so Vite's normal env handling and
    // the `?? 'http://localhost:8000'` fallback in src/services/api.ts still apply.
    define:
      resolved === undefined
        ? {}
        : { 'import.meta.env.VITE_API_URL': JSON.stringify(resolved) },
    server: {
      port: 3000,
    },
  }
})
