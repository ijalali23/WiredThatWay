// Brand 3-font system, self-hosted locally (media/fonts/*.woff2) rather than fetched from
// Google's CDN at render time. This sandbox's headless-Chrome render process doesn't trust
// the outbound proxy's TLS-terminating CA (curl/Node do, via NODE_EXTRA_CA_CERTS; Chrome's
// ephemeral render profile doesn't), so any @remotion/google-fonts loadFont() call that
// requires a live fetch to fonts.gstatic.com fails every render with ERR_CERT_AUTHORITY_INVALID
// and never resolves. Same font files, same family names/weights as before — just local.
import { staticFile } from 'remotion';

const face = (family: string, file: string, weight: string) =>
  `@font-face { font-family: '${family}'; src: url('${staticFile(`fonts/${file}`)}') format('woff2'); font-weight: ${weight}; font-style: normal; font-display: block; }`;

const css = [
  face('Space Grotesk', 'space-grotesk.woff2', '500 700'),
  face('Inter', 'inter.woff2', '400 600'),
  face('JetBrains Mono', 'jetbrains-mono.woff2', '400 700'),
  face('Spectral', 'spectral-500.woff2', '500'),
  face('Spectral', 'spectral-600.woff2', '600'),
  face('Source Serif Four', 'source-serif-4.woff2', '600 900'),
].join('\n');

if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
}

export const FONT_DISPLAY = 'Space Grotesk';
export const FONT_BODY = 'Inter';
export const FONT_MONO = 'JetBrains Mono';
// serif for the Claude Code wordmark clone (close match to the app's serif)
export const FONT_SERIF = 'Spectral';
// heavy editorial serif for the vox collage engine's headlines (Publico-ish; Spectral maxes
// at 600 and reads too light/bookish over collage layers)
export const FONT_EDITORIAL = 'Source Serif Four';
