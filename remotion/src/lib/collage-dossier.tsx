import React, { useContext } from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { FONT_BODY, FONT_EDITORIAL } from '../fonts';
import { VOX, Layer, EASE_OUT, EASE_PLACE } from './collage';

// =============================================================================
// "Dossier" skin — an alternate visual language on top of the same collage
// engine (CollageBoard/Layer/camera/parallax all still apply). Modeled on a
// reference "investigative archive / scrapbook" look: black textured paper +
// cream paper torn apart, yellow marker annotations, grid paper, tape, and
// stamped black-box headline chips. See vox-shorts/NOTES on reference clips
// for the source analysis — the reference clips themselves are AI-generated
// video with hallucinated background text, so nothing here copies their text;
// only the layout/graphic language is reused, with real driven data as always.
// =============================================================================

export const DOSSIER = {
  black: '#161412', // textured "black paper" ground, not pure #000 (reads as paper, not void)
  blackDeep: '#0d0c0a',
  grid: 'rgba(232,183,58,0.16)', // faint yellow gridlines over black
  cream: VOX.cream,
  paper: VOX.paper,
  ink: VOX.ink,
  yellow: VOX.yellow,
} as const;

// -----------------------------------------------------------------------------
// GridLines — faint graph-paper ruling. Standalone (usable inside any panel)
// or as the `overlay` of DarkPaperBG/PaperPanel below.
// -----------------------------------------------------------------------------
export const GridLines: React.FC<{ w: number; h: number; cell?: number; color?: string; opacity?: number }> = ({
  w,
  h,
  cell = 44,
  color = DOSSIER.grid,
  opacity = 1,
}) => (
  <svg width={w} height={h} style={{ position: 'absolute', left: 0, top: 0, opacity }}>
    <defs>
      <pattern id={`grid-${cell}`} width={cell} height={cell} patternUnits="userSpaceOnUse">
        <path d={`M ${cell} 0 L 0 0 0 ${cell}`} fill="none" stroke={color} strokeWidth={1} />
      </pattern>
    </defs>
    <rect width={w} height={h} fill={`url(#grid-${cell})`} />
  </svg>
);

// -----------------------------------------------------------------------------
// DarkPaperBG — the board surface for "space/data" panels: black textured
// paper + grid ruling + soft vignette. Same depth convention as PaperBG.
// -----------------------------------------------------------------------------
const CamCtxShape = { offX: 0, offY: 0, zoom: 1 };
export const DarkPaperBG: React.FC<{ w: number; h: number; depth?: number; grid?: boolean }> = ({ w, h, depth = -0.06, grid = true }) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: -w * 0.05,
        top: -h * 0.05,
        width: w * 1.1,
        height: h * 1.1,
        background: `radial-gradient(ellipse at 50% 40%, ${DOSSIER.black} 0%, ${DOSSIER.blackDeep} 100%)`,
      }}
    >
      {grid ? <GridLines w={w * 1.1} h={h * 1.1} /> : null}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 100%)' }} />
    </div>
  );
};

// -----------------------------------------------------------------------------
// TornDivider — a jagged rip between two panels. Renders as an SVG mask edge;
// place it centered ON the seam (x = seam position for vertical, y for
// horizontal). Deterministic jitter (no Math.random) so it's stable across
// re-renders and frames. `side` says which side gets the white "torn paper
// fibre" highlight (the side that would show its ragged edge).
// -----------------------------------------------------------------------------
const jag = (seed: number, i: number) => {
  // deterministic pseudo-random in [-1, 1], stable per (seed, i)
  const v = Math.sin(seed * 12.9898 + i * 78.233) * 43758.5453;
  return (v - Math.floor(v)) * 2 - 1;
};

export const TornDivider: React.FC<{
  orientation: 'vertical' | 'horizontal';
  pos: number; // seam x (vertical) or y (horizontal), canvas px
  spanStart: number;
  spanEnd: number;
  amplitude?: number;
  seed?: number;
  z?: number;
}> = ({ orientation, pos, spanStart, spanEnd, amplitude = 14, seed = 1, z }) => {
  const teeth = 22;
  const step = (spanEnd - spanStart) / teeth;
  const pts: [number, number][] = [];
  for (let i = 0; i <= teeth; i++) {
    const along = spanStart + step * i;
    const off = jag(seed, i) * amplitude;
    pts.push(orientation === 'vertical' ? [pos + off, along] : [along, pos + off]);
  }
  const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ');
  return (
    <svg style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible', zIndex: z, pointerEvents: 'none' }}>
      {/* the rip line itself: a soft white fibre highlight + a dark hairline shadow just under it */}
      <path d={d} fill="none" stroke="rgba(0,0,0,0.35)" strokeWidth={5} transform="translate(2,3)" />
      <path d={d} fill="none" stroke={DOSSIER.cream} strokeWidth={4} strokeLinejoin="round" />
    </svg>
  );
};

// -----------------------------------------------------------------------------
// TapeStrip — standalone piece of tape at an arbitrary board position/angle
// (collage.tsx's ArchivalPhoto has its own inline corner tape; this is the
// general-purpose version for dossier layouts — pinning photos, clippings).
// -----------------------------------------------------------------------------
export const TapeStrip: React.FC<{ x: number; y: number; w?: number; rotate?: number; z?: number }> = ({
  x,
  y,
  w = 130,
  rotate = -8,
  z,
}) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: w,
      height: w * 0.32,
      background: 'rgba(220,210,182,0.72)',
      boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
      transform: `translate(-50%, -50%) rotate(${rotate}deg)`,
      zIndex: z,
    }}
  />
);

// -----------------------------------------------------------------------------
// Crosshair — small reticle glyph, pure decoration (texture density, like the
// reference's scattered "+" / target-circle marks).
// -----------------------------------------------------------------------------
export const Crosshair: React.FC<{ x: number; y: number; size?: number; variant?: 'plus' | 'target'; color?: string; z?: number }> = ({
  x,
  y,
  size = 22,
  variant = 'plus',
  color = DOSSIER.yellow,
  z,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    style={{ position: 'absolute', left: x - size / 2, top: y - size / 2, zIndex: z }}
  >
    {variant === 'plus' ? (
      <path d="M12 3 L12 9 M12 15 L12 21 M3 12 L9 12 M15 12 L21 12" stroke={color} strokeWidth={2} strokeLinecap="round" />
    ) : (
      <>
        <circle cx={12} cy={12} r={7} fill="none" stroke={color} strokeWidth={1.6} />
        <circle cx={12} cy={12} r={1.6} fill={color} />
      </>
    )}
  </svg>
);

// -----------------------------------------------------------------------------
// ChevronStack — a small column of upward chevrons (secondary graphic motif
// next to arrows/callouts). Count/gap/size tuned to read at a glance.
// -----------------------------------------------------------------------------
export const ChevronStack: React.FC<{ x: number; y: number; count?: number; size?: number; color?: string; gap?: number; z?: number }> = ({
  x,
  y,
  count = 4,
  size = 26,
  color = DOSSIER.yellow,
  gap = 20,
  z,
}) => (
  <div style={{ position: 'absolute', left: x, top: y, transform: 'translate(-50%, -50%)', zIndex: z }}>
    {Array.from({ length: count }).map((_, i) => (
      <svg key={i} width={size} height={size * 0.55} viewBox="0 0 24 14" style={{ display: 'block', marginTop: i === 0 ? 0 : gap - size * 0.55, opacity: 0.4 + (0.6 * (i + 1)) / count }}>
        <path d="M2 12 L12 3 L22 12" fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ))}
  </div>
);

// -----------------------------------------------------------------------------
// DossierLabel — the black-box, white-headline, yellow-kicker chip (matches
// "1946: THE FIRST PHOTO" style callouts) — the dark-panel sibling of
// collage.tsx's LabelChip (which is cream/light-panel only).
// -----------------------------------------------------------------------------
export const DossierLabel: React.FC<{
  kicker?: string;
  text: string;
  x: number;
  y: number;
  at?: number;
  size?: number;
  align?: 'left' | 'center';
  z?: number;
}> = ({ kicker, text, x, y, at = 0, size = 44, align = 'left', z }) => (
  <Layer x={x} y={y} w={size * Math.max(text.length, (kicker ?? '').length) * 0.62 + 60} at={at} dur={8} enter="pop" rotate={0} depth={0.02} drift={0.5} z={z}>
    <div style={{ textAlign: align, display: 'inline-block' }}>
      {kicker ? (
        <div
          style={{
            display: 'inline-block',
            fontFamily: FONT_BODY,
            fontWeight: 800,
            fontSize: size * 0.62,
            letterSpacing: 1,
            color: DOSSIER.yellow,
            background: DOSSIER.black,
            padding: `${size * 0.14}px ${size * 0.3}px`,
            marginBottom: size * 0.1,
          }}
        >
          {kicker}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: FONT_EDITORIAL,
          fontWeight: 900,
          fontSize: size,
          lineHeight: 1.05,
          color: DOSSIER.cream,
          background: '#000',
          padding: `${size * 0.12}px ${size * 0.28}px`,
          boxShadow: '4px 4px 0 rgba(0,0,0,0.4)',
          display: 'inline-block',
        }}
      >
        {text}
      </div>
    </div>
  </Layer>
);

// -----------------------------------------------------------------------------
// MarkerArrow — thick hand-drawn-style arrow (the reference's yellow marker
// annotation strokes). Thin wrapper preset around collage.tsx's SketchArrow
// with dossier defaults (thicker, yellow, slightly wobbly path expected from
// caller — feed a path with 1-2 gentle bends, not a perfect straight line).
// Re-exported here rather than duplicated: use SketchArrow directly from
// '../lib/collage' with color={DOSSIER.yellow} width={12} for the same effect.
// -----------------------------------------------------------------------------
export { SketchArrow } from './collage';
