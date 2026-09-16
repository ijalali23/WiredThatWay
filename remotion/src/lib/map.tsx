// Geography-shorts kit — a REAL Mercator projection over REAL lat/lon country outlines
// (src/lib/geo/world.ts, Natural Earth 110m, public domain). Seeds short-11 ("the map lied"),
// and is built generic enough for the rest of the niche: the only country inside a country,
// the straightest border, time-zone weirdness, "every map is wrong" (Peters/Robinson).
//
// THE POINT OF THIS LIB: we do not FAKE the distortion. `mercY` is the actual Mercator
// formula, and "sliding a country to the equator" literally shifts its true coordinates and
// re-projects them — so the shrink EMERGES from the projection instead of being an animation
// someone hand-tuned. The map lies on camera, using our own code, the way it lies on a wall.
// (Same ethos as prob.tsx's seeded Monty Carlo sim and gen_chords' real equal temperament.)
import React from 'react';
import { Country, Ring, WORLD } from './geo/world';
import { FONT_BODY, FONT_DISPLAY } from '../fonts';

export type { Country, Ring };

// =============================================================================
// THE PROJECTION — y = ln(tan(π/4 + φ/2)). Everything else in this file is a consequence.
// =============================================================================
export const MAX_LAT = 85.05; // Mercator sends the poles to infinity; clamp like every web map

export const mercY = (lat: number): number => {
  const c = Math.max(-MAX_LAT, Math.min(MAX_LAT, lat));
  return Math.log(Math.tan(Math.PI / 4 + (c * Math.PI) / 180 / 2));
};

export type MapScale = {
  px: (lon: number, lat: number) => [number, number];
  box: { x: number; y: number; w: number; h: number };
  k: number; // pixels per radian of Mercator space
};

// Fit lonRange x latRange into a pixel box. The vertical scale is NOT free: Mercator is
// conformal, so x and y must share one k or the shapes shear. We honour that and let the
// resulting height be whatever the projection says it is.
export const makeMapScale = (
  lonRange: [number, number],
  latRange: [number, number],
  box: { x: number; y: number; w: number },
): MapScale => {
  const x0 = (lonRange[0] * Math.PI) / 180;
  const x1 = (lonRange[1] * Math.PI) / 180;
  const k = box.w / (x1 - x0);
  const yTop = mercY(latRange[1]);
  const yBot = mercY(latRange[0]);
  const h = (yTop - yBot) * k;
  return {
    k,
    box: { ...box, h },
    px: (lon, lat) => [box.x + ((lon * Math.PI) / 180 - x0) * k, box.y + (yTop - mercY(lat)) * k],
  };
};

// =============================================================================
// TRANSPORT — carrying a country to another latitude WITHOUT changing its real size.
//
// The naive move (add dLat, add dLon to every vertex) is WRONG, and wrong in a way that looks
// plausible until you render it: Mercator's x depends only on longitude, so a country dragged
// south keeps every degree of its longitude span while its height compresses. Greenland arrives
// at the equator squashed and far too wide — it flattens instead of shrinking.
//
// The real correction is the convergence of the meridians: one degree of longitude is
// 111 km * cos(lat) of ground, so as a vertex moves from lat to lat', its east-west offset from
// the country's centre must rescale by cos(lat)/cos(lat'). Do that, and the country arrives at
// its true size — because it kept its true ground dimensions the whole way down. The shrink is
// still EMERGENT (it falls out of real spherical geometry), never a keyframed scale.
// =============================================================================
export type Move = { toLon: number; toLat: number };

const COS_MIN = Math.cos((MAX_LAT * Math.PI) / 180);
const cosLat = (lat: number) => Math.max(COS_MIN, Math.cos((lat * Math.PI) / 180));

// Vertex position when the country has been carried `t` (0..1) of the way to its target.
const transportPt = (
  lon: number,
  lat: number,
  cLon: number,
  cLat: number,
  dLon: number,
  dLat: number,
  t: number,
): [number, number] => {
  const latN = lat + dLat * t;
  const k = cosLat(lat) / cosLat(latN); // meridians converge/diverge — the whole trick
  const lonN = cLon + dLon * t + (lon - cLon) * k;
  return [lonN, latN];
};

const ringPath = (s: MapScale, ring: Ring, tp: (lon: number, lat: number) => [number, number]): string => {
  let d = '';
  for (let i = 0; i < ring.length; i++) {
    const [lon, lat] = tp(ring[i][0], ring[i][1]);
    const [x, y] = s.px(lon, lat);
    d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }
  return d + 'Z';
};

// The identity transport (t = 0) — a country drawn where it actually is.
export const countryPath = (s: MapScale, c: Country): string =>
  c.rings.map((r) => ringPath(s, r, (lon, lat) => [lon, lat])).join(' ');

const mover = (c: Country, m: Move, t: number) => {
  const [cLon, cLat] = centroid(c);
  const dLon = m.toLon - cLon;
  const dLat = m.toLat - cLat;
  return (lon: number, lat: number) => transportPt(lon, lat, cLon, cLat, dLon, dLat, t);
};

export const movedPath = (s: MapScale, c: Country, m: Move, t: number): string =>
  c.rings.map((r) => ringPath(s, r, mover(c, m, t))).join(' ');

// Where the country's centre has got to — for pinning a label to it mid-flight.
export const movedCentroid = (c: Country, m: Move, t: number): [number, number] => {
  const [cLon, cLat] = centroid(c);
  return [cLon + (m.toLon - cLon) * t, cLat + (m.toLat - cLat) * t];
};

// =============================================================================
// MEASUREMENT — how big does a country LOOK right now? Shoelace over the projected polygon,
// in pixels. This is what the eye is actually being told, and it is what we put on screen.
// =============================================================================
export const projectedArea = (s: MapScale, c: Country, m?: Move, t = 0): number => {
  const tp = m ? mover(c, m, t) : (lon: number, lat: number): [number, number] => [lon, lat];
  let total = 0;
  for (const ring of c.rings) {
    let a = 0;
    for (let i = 0; i < ring.length; i++) {
      const [lo1, la1] = tp(ring[i][0], ring[i][1]);
      const [lo2, la2] = tp(ring[(i + 1) % ring.length][0], ring[(i + 1) % ring.length][1]);
      const [x1, y1] = s.px(lo1, la1);
      const [x2, y2] = s.px(lo2, la2);
      a += x1 * y2 - x2 * y1;
    }
    total += Math.abs(a) / 2;
  }
  return total;
};

// How many times bigger the map DRAWS this country than it would at the equator. The number the
// video is about: ~15x for Greenland, ~4.7x for Canada, ~1x for anything on the equator. Measured
// off the projected polygon, not asserted.
export const inflation = (s: MapScale, c: Country): number => {
  const [cLon] = centroid(c);
  const equator: Move = { toLon: cLon, toLat: 0 };
  return projectedArea(s, c) / Math.max(1e-9, projectedArea(s, c, equator, 1));
};

// =============================================================================
// REAL-WORLD DISTANCE — for "how wide is X really" claims (vox-5's Indonesia/US comparison
// and any future one). Great-circle, not a flat-map pixel measurement, so it's the actual
// ground distance regardless of which projection is on screen.
// =============================================================================
export const greatCircleKm = (lon1: number, lat1: number, lon2: number, lat2: number): number => {
  const R = 6371; // mean Earth radius, km
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dphi = toRad(lat2 - lat1);
  const dlam = toRad(lon2 - lon1);
  const a = Math.sin(dphi / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dlam / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
};

// The real east-west extent of a (possibly multi-ring/archipelago) shape: the great-circle
// distance between its westernmost and easternmost real points, not a longitude-degree count
// (which would overstate distance near the poles and understate it at the equator).
export const eastWestExtentKm = (rings: Ring[]): number => {
  const pts = rings.flat();
  const west = pts.reduce((a, b) => (a[0] < b[0] ? a : b));
  const east = pts.reduce((a, b) => (a[0] > b[0] ? a : b));
  return greatCircleKm(west[0], west[1], east[0], east[1]);
};

export const centroid = (c: Country): [number, number] => {
  let lo = 0;
  let la = 0;
  let n = 0;
  for (const ring of c.rings) {
    for (const [x, y] of ring) {
      lo += x;
      la += y;
      n++;
    }
  }
  return [lo / n, la / n];
};


// =============================================================================
// EQUAL EARTH PROJECTION — Šavrič, Jenny & Patterson (2018), the exact published polynomial
// (doi.org/10.1080/13658816.2018.1504949), not an approximation. Same ethos as mercY: this
// is the real formula, so the true relative sizes of Africa and Greenland fall out of the
// math, they aren't drawn to match a number someone typed in.
// =============================================================================
const EE_A1 = 1.340264;
const EE_A2 = -0.081106;
const EE_A3 = 0.000893;
const EE_A4 = 0.003796;
const EE_M = Math.sqrt(3) / 2;

// Raw projected coordinates in the projection's own units (not yet fit to a pixel box).
export const equalEarthXY = (lon: number, lat: number): [number, number] => {
  const lam = (lon * Math.PI) / 180;
  const phi = (lat * Math.PI) / 180;
  const theta = Math.asin(EE_M * Math.sin(phi));
  const t2 = theta * theta;
  const t3 = t2 * theta;
  const t6 = t3 * t3;
  const t7 = t6 * theta;
  const t8 = t6 * t2;
  const t9 = t8 * theta;
  const x =
    (2 * Math.sqrt(3) * lam * Math.cos(theta)) / (3 * (9 * EE_A4 * t8 + 7 * EE_A3 * t6 + 3 * EE_A2 * t2 + EE_A1));
  const y = EE_A4 * t9 + EE_A3 * t7 + EE_A2 * t3 + EE_A1 * theta;
  return [x, y];
};

export type EqualEarthScale = { px: (lon: number, lat: number) => [number, number]; box: { x: number; y: number; w: number; h: number } };

// Equal-area means ONE scale for the whole globe: unlike makeMapScale (free to crop any
// lon/lat window), the projection itself fixes the world's aspect ratio — we only choose how
// many pixels that fixed shape gets, never stretch it, or we'd be re-introducing the exact
// distortion this projection exists to remove.
export const makeEqualEarthScale = (box: { x: number; y: number; w: number }): EqualEarthScale => {
  const [xMax] = equalEarthXY(180, 0);
  const [, yMax] = equalEarthXY(0, 90);
  const k = box.w / (2 * xMax);
  const h = 2 * yMax * k;
  return {
    box: { ...box, h },
    px: (lon, lat) => {
      const [x, y] = equalEarthXY(lon, lat);
      return [box.x + box.w / 2 + x * k, box.y + h / 2 - y * k];
    },
  };
};

export const equalEarthCountryPath = (s: EqualEarthScale, c: Country): string =>
  c.rings
    .map((ring) => {
      let d = '';
      for (let i = 0; i < ring.length; i++) {
        const [x, y] = s.px(ring[i][0], ring[i][1]);
        d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
      }
      return `${d}Z`;
    })
    .join(' ');

export const EqualEarthWorldLayer: React.FC<{
  scale: EqualEarthScale;
  except?: string[];
  fill?: string;
  stroke?: string;
  opacity?: number;
}> = ({ scale, except = [], fill = '#233042', stroke = '#31425a', opacity = 1 }) => (
  <g opacity={opacity}>
    {WORLD.filter((c) => c.cont !== 'Antarctica' && !except.includes(c.name)).map((c) => (
      <path key={c.name} d={equalEarthCountryPath(scale, c)} fill={fill} stroke={stroke} strokeWidth={1} />
    ))}
  </g>
);

// Real ground truth for any "how many times bigger" claim in this series — summed straight
// from Natural Earth's own km2 figures, never typed in by hand. Generic (any country/continent
// predicate) so each new vox-N video doesn't need its own one-off ratio function.
export const sumKm2 = (predicate: (c: Country) => boolean): number =>
  WORLD.filter(predicate).reduce((sum, c) => sum + c.km2, 0);

export const areaRatio = (a: (c: Country) => boolean, b: (c: Country) => boolean): number =>
  sumKm2(a) / Math.max(1, sumKm2(b));

// Africa ≈ 29.9M km2 / Greenland ≈ 2.19M km2 ≈ 13.6x, which is where "about 14 times" (the
// figure NASA/NPR/WaPo all reported) actually comes from.
export const africaGreenlandRatio = (): number =>
  areaRatio((c) => c.cont === 'Africa', (c) => c.name === 'Greenland');

// =============================================================================
// LAYERS
// =============================================================================
export const WorldLayer: React.FC<{
  scale: MapScale;
  except?: string[]; // drawn separately on top by the shot
  fill?: string;
  stroke?: string;
  opacity?: number;
}> = ({ scale, except = [], fill = '#233042', stroke = '#31425a', opacity = 1 }) => (
  <g opacity={opacity}>
    {WORLD.filter((c) => c.cont !== 'Antarctica' && !except.includes(c.name)).map((c) => (
      <path key={c.name} d={countryPath(scale, c)} fill={fill} stroke={stroke} strokeWidth={1} />
    ))}
  </g>
);

export const CountryShape: React.FC<{
  scale: MapScale;
  country: Country;
  move?: Move; // where it is being carried to
  t?: number; // 0 = home, 1 = arrived (at its TRUE size)
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  opacity?: number;
  glow?: boolean;
}> = ({ scale, country, move, t = 0, fill, stroke, strokeWidth = 2.5, opacity = 1, glow = false }) => (
  <path
    d={move ? movedPath(scale, country, move, t) : countryPath(scale, country)}
    fill={fill}
    stroke={stroke ?? fill}
    strokeWidth={strokeWidth}
    strokeLinejoin="round"
    opacity={opacity}
    style={glow ? { filter: `drop-shadow(0 0 18px ${fill})` } : undefined}
  />
);

// The graticule is evidence, not decoration: equally-spaced parallels drift further and
// further apart as they climb north. That IS the distortion, drawn.
export const Graticule: React.FC<{
  scale: MapScale;
  lats?: number[];
  color?: string;
  opacity?: number;
}> = ({ scale, lats = [-60, -30, 0, 30, 60, 80], color = '#5b7a99', opacity = 0.25 }) => {
  const { box } = scale;
  return (
    <g opacity={opacity}>
      {lats.map((lat) => {
        const [, y] = scale.px(0, lat);
        const eq = lat === 0;
        return (
          <line
            key={lat}
            x1={box.x}
            x2={box.x + box.w}
            y1={y}
            y2={y}
            stroke={color}
            strokeWidth={eq ? 2.5 : 1.5}
            strokeDasharray={eq ? undefined : '8 10'}
          />
        );
      })}
    </g>
  );
};

// =============================================================================
// LABEL — a plated chip pinned to a country (in map pixels), with an optional big stat.
// =============================================================================
export const MapLabel: React.FC<{
  x: number;
  y: number;
  title: string;
  stat?: string;
  color: string;
  size?: number;
  opacity?: number;
  scaleUp?: number; // swell when the narrator says this one
  anchor?: 'middle' | 'start' | 'end';
}> = ({ x, y, title, stat, color, size = 34, opacity = 1, scaleUp = 0, anchor = 'middle' }) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(${anchor === 'middle' ? '-50%' : anchor === 'end' ? '-100%' : '0'}, -50%) scale(${
        1 + 0.12 * scaleUp
      })`,
      opacity,
      background: 'rgba(13,17,23,0.86)',
      border: `2px solid ${color}${scaleUp > 0.5 ? 'cc' : '55'}`,
      borderRadius: 14,
      padding: '8px 16px',
      textAlign: 'center',
      whiteSpace: 'nowrap',
    }}
  >
    <div
      style={{
        fontFamily: FONT_BODY,
        fontWeight: 700,
        fontSize: size * 0.72,
        letterSpacing: 3,
        textTransform: 'uppercase',
        color,
      }}
    >
      {title}
    </div>
    {stat ? (
      <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: size, color: '#fff', marginTop: 2 }}>
        {stat}
      </div>
    ) : null}
  </div>
);
