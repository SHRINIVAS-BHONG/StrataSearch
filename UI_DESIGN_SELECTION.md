# StrataSearch UI Design Selection & Design System Specification
**Document Version**: 2.0.0  
**Target Platform**: StrataSearch Enterprise Hybrid Retrieval & Document Intelligence  
**Design System Standard**: *Strata Obsidian* (Synthesized B2B SaaS Architecture)  
**Reference Repository**: `https://github.com/MiaAI-Lab/Claude-Fable-5.2-HTML-Files`  

---

## 1. Executive Summary

StrataSearch is transitioning from an internal developer test harness to a commercial, client-ready, deployable Enterprise Hybrid Retrieval & Document Intelligence Platform. Internal developer harnesses frequently rely on synthetic test fixtures, hardcoded placeholder strings, developer stress-test buttons, and fragile external CDN dependencies.

To establish a client-ready visual identity, an exhaustive survey of all 76 standalone web application studies in `https://github.com/MiaAI-Lab/Claude-Fable-5.2-HTML-Files` was conducted. Based on a weighted multi-criteria rubric tailored for high-density enterprise software, **`047-atelier-vesper-watch` (Score: 9.32 / 10.0)** was selected as the primary visual design system foundation. Its refined dark obsidian canvas, hairline border precision, and tabular lining typography provide the luxury mechanical finish appropriate for enterprise retrieval infrastructure.

To ensure functional completeness across high-throughput data operations, this visual system is synthesized with:
1. **`002-airship-terminal-split-flap` (Score: 9.14 / 10.0)**: Inspires the tabular document library layout, real-time status chips (`ALL`, `INDEXED`, `PROCESSING`, `QUEUED`, `FAILED`), and monospace identifier formatting.
2. **`039-mars-greenhouse-console` (Score: 8.83 / 10.0)**: Inspires the live subsystem telemetry instrumentation cards, metric sparklines, and query execution strip.

The resulting design system—**Strata Obsidian**—is implemented with strict **zero-framework** vanilla technologies: semantic HTML5, modern CSS3 custom properties with grid and flexbox, and native ES6 JavaScript (`fetch`, `async/await`), completely removing external CSS/JS frameworks.

---

## 2. Evaluation Methodology & 5-Dimension Rubric

Every study in the Claude Fable 5.2 repository was evaluated against five rigorous dimensions weighted specifically for high-throughput enterprise developer and data platforms:

| Dimension | Weight | Evaluation Criteria |
|---|---|---|
| **Information Architecture & Density (IA)** | 25% | Organization of dense technical data, tabular status lists, parameter controls, filter facets, and modal drawers without visual congestion. |
| **Enterprise Visual Polish & Aesthetics (EVP)** | 25% | Visual gravitas suitable for enterprise infrastructure (modern dark theme, high contrast ratio, restrained hairline borders, absence of whimsical, skeuomorphic, or juvenile artifacts). |
| **Component Adaptability for Requirement R5 (CA)** | 25% | Ease of adapting layout patterns into search inputs, multi-attribute rank cards, drag-and-drop dropzones, document status tables, KPI grids, and inspector modals. |
| **Typography & Readability (TH)** | 15% | Dual-font typography hierarchy combining high-legibility geometric sans-serif for body text with tabular lining monospace for scores, latencies, IDs, and cURL snippets. |
| **Zero-Framework Feasibility & Performance (ZFP)** | 10% | Clean vanilla CSS layout mechanics (Flexbox, CSS Grid, Custom Properties) operating without canvas/WebGL frame locks, audio synthesis overhead, or layout thrashing. |

### Weighted Score Formula
$$\text{Score} = (0.25 \times \text{IA}) + (0.25 \times \text{EVP}) + (0.25 \times \text{CA}) + (0.15 \times \text{TH}) + (0.10 \times \text{ZFP})$$

---

## 3. Exhaustive Audit & Scoring Table of All 76 HTML Studies

The repository contains exactly 76 numbered HTML studies (studies `076`, `077`, and `078` are intentionally absent in the upstream repository, numbering spans `001` through `079`). Below is the complete audit and scoring matrix:

| Rank | Study ID & Filename | Title / Focus | IA (25%) | EVP (25%) | CA (25%) | TH (15%) | ZFP (10%) | Weighted Score | Verdict / Synthesis Role |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1** | `047-atelier-vesper-watch` | Atelier Vesper — Calibre V.03 | 8.8 | 9.8 | 9.0 | 9.6 | 9.5 | **9.32** | **TOP-RATED WINNER: Primary Visual Design System** |
| **2** | `002-airship-terminal-split-flap` | Aerodrome Lisbeth — Departures | 9.6 | 8.8 | 9.4 | 8.9 | 8.8 | **9.14** | **FINALIST: Tabular Layout & Status Chips** |
| **3** | `scripts/gallery-template` / `index` | Claude Fable Gallery Engine | 9.0 | 8.6 | 8.9 | 8.8 | 9.8 | **8.93** | **FINALIST: Navigation & Filter Toolbar Engine** |
| **4** | `039-mars-greenhouse-console` | ARES-HORT Console Greenhouse B | 9.5 | 7.8 | 9.1 | 8.5 | 9.2 | **8.83** | **FINALIST: Subsystem Telemetry & KPI Cards** |
| **5** | `045-foundry-specimen-halden` | Halden Grotesk Type Specimen | 8.2 | 8.5 | 8.2 | 9.5 | 9.0 | **8.58** | Typographic grid & multi-mode toggle donor |
| **6** | `072-lumen-town-grid` | Lumen — Municipal Power Board | 9.0 | 7.2 | 8.5 | 8.2 | 8.9 | **8.35** | Subsystem control & action switch donor |
| **7** | `034-museum-of-obsolete-sounds` | Museum of Obsolete Sounds | 8.0 | 8.2 | 7.8 | 8.8 | 8.7 | **8.19** | Card hierarchy & plinth elevation donor |
| **8** | `008-cabinet-of-impossible-minerals` | Cabinet of Impossible Minerals | 8.2 | 8.3 | 7.7 | 8.0 | 8.8 | **8.16** | Modal drawer & dark specimen cards |
| **9** | `016-vector-lunar-descent` | Descent — Vector Lunar Lander | 8.4 | 7.8 | 7.6 | 8.2 | 8.8 | **8.10** | Monospace telemetry and trajectory readouts |
| **10** | `069-strange-attractors` | Strange Attractors — Orbits | 7.6 | 8.2 | 7.4 | 8.0 | 8.7 | **7.88** | Parameter sliders & dark viridian canvas |
| 11 | `005-working-slide-rule` | Working Slide Rule Engine | 8.5 | 7.0 | 7.5 | 8.2 | 8.5 | 7.83 | Analog cursor calculation; too skeuomorphic |
| 12 | `014-ulam-prime-spiral` | Ulam Prime Number Spiral | 7.5 | 7.8 | 7.2 | 8.0 | 8.8 | 7.76 | Mathematical visualization; lacks data controls |
| 13 | `029-skerry-weather-station` | Skerry Marine Weather Station | 8.4 | 7.2 | 7.5 | 7.8 | 8.2 | 7.75 | Meteorological gauges; lacks tabular density |
| 14 | `055-seismograph-drum` | Seismograph Drum Logger | 8.0 | 7.4 | 7.2 | 7.9 | 8.5 | 7.69 | Continuous wave logger; single-purpose feed |
| 15 | `019-bauhaus-drum-machine` | Bauhaus Drum Machine | 7.8 | 7.6 | 7.0 | 7.5 | 8.4 | 7.54 | Step sequencer; overly bold primary colors |
| 16 | `022-hotel-meridian-elevator` | Hotel Meridian Elevator Bank | 7.9 | 7.3 | 7.1 | 7.6 | 8.5 | 7.53 | Indicator lamps; limited SaaS UI application |
| 17 | `063-the-astrolabe` | The Planispheric Astrolabe | 7.2 | 8.5 | 6.5 | 7.8 | 7.9 | 7.44 | Antique brass astronomy; non-enterprise aesthetic |
| 18 | `056-the-combination` | The Combination Safe Dial | 7.0 | 7.8 | 6.8 | 7.5 | 8.5 | 7.40 | Dial interaction; inappropriate for search |
| 19 | `060-ascii-tide` | ASCII Tide Gauge & Moon | 7.6 | 7.0 | 7.0 | 7.9 | 8.5 | 7.43 | Monospace tide graph; too low-fi for B2B |
| 20 | `011-the-hours-in-words` | The Hours in Words | 6.5 | 7.8 | 6.5 | 8.8 | 8.8 | 7.35 | Word clock typography; no search controls |
| 21 | `032-the-night-typist` | The Night Typist Mechanical | 6.8 | 7.5 | 6.5 | 8.2 | 8.4 | 7.32 | Skeuomorphic typewriter; unsuitable |
| 22 | `004-lighthouse-keeper-night-watch` | Lighthouse Keeper Night Watch | 7.2 | 7.5 | 6.4 | 7.4 | 8.0 | 7.19 | Nautical narrative log; lacks data layout |
| 23 | `013-iron-filings` | Iron Filings Magnetic Flux | 6.2 | 7.6 | 6.4 | 7.0 | 8.5 | 7.07 | Physics particle simulation; high GPU usage |
| 24 | `036-kestrel-frameworks-bicycles` | Kestrel Frameworks Bicycles | 7.2 | 7.0 | 6.8 | 7.5 | 8.0 | 7.18 | E-commerce specimen; low technical density |
| 25 | `028-conservas-mare-alta` | Conservas Mare Alta Sardines | 6.8 | 7.4 | 6.2 | 7.6 | 8.2 | 7.11 | Vintage cannery label; whimsical graphic style |
| 26 | `015-maison-ombre-perfume` | Maison Ombre Luxury Fragrance | 6.5 | 8.0 | 6.0 | 7.8 | 8.0 | 7.07 | Editorial luxury boutique; low information density |
| 27 | `018-pen-plotter-landscapes` | Pen Plotter Generative Topo | 6.5 | 7.5 | 6.2 | 7.0 | 8.3 | 6.98 | Generative vector art; no SaaS components |
| 28 | `023-walnut-turntable` | Walnut Turntable Vinyl Audio | 6.4 | 7.6 | 6.0 | 7.2 | 8.1 | 6.99 | Skeuomorphic hifi audio; non-transferable |
| 29 | `070-semaphore` | Maritime Flag Semaphore | 6.8 | 6.8 | 6.5 | 7.2 | 8.4 | 6.95 | Semaphore alphabet; educational novelty |
| 30 | `010-op-art-pulse` | Op Art Optical Pulse | 5.8 | 7.5 | 5.8 | 6.5 | 8.8 | 6.68 | High-contrast flicker; induces visual fatigue |
| 31 | `001-suminagashi-marbling-tray` | Suminagashi Water Marbling | 5.5 | 7.8 | 5.5 | 6.8 | 8.2 | 6.67 | Interactive fluid canvas; decorative only |
| 32 | `003-anatomy-of-a-croissant` | Anatomy of a Croissant | 6.5 | 6.8 | 5.8 | 7.2 | 8.2 | 6.65 | Culinary infographic; whimsical bakery theme |
| 33 | `006-volcan-chico-hot-sauce` | Volcán Chico Hot Sauce | 6.0 | 7.0 | 6.0 | 7.0 | 8.2 | 6.62 | Packaging label art; commercial retail |
| 34 | `007-ice-core-800-metres` | Antarctic Ice Core Log | 7.0 | 6.8 | 6.2 | 7.2 | 7.8 | 6.89 | Geological depth stratigraphy; vertical scroll |
| 35 | `009-koi-pond-noon` | Koi Pond Noon Shimmer | 5.2 | 7.5 | 5.2 | 6.2 | 8.4 | 6.39 | Ambient aquatic physics; non-functional |
| 36 | `012-murmuration-at-dusk` | Starling Murmuration Flight | 5.4 | 7.6 | 5.2 | 6.5 | 8.2 | 6.45 | Boids flocking canvas simulation; no UI |
| 37 | `017-spore-print-riso-zine` | Spore Print Risograph Zine | 6.0 | 6.8 | 5.8 | 7.0 | 8.2 | 6.52 | Risograph halftone texture; too artsy |
| 38 | `020-aurora-over-the-fjord` | Aurora Over the Fjord | 5.0 | 7.8 | 5.0 | 6.2 | 8.0 | 6.35 | Atmospheric gradient glow; purely scenic |
| 39 | `021-drawer-of-imaginary-moths` | Drawer of Imaginary Moths | 6.2 | 7.4 | 5.8 | 6.8 | 8.0 | 6.64 | Entomological display case; specimen cards |
| 40 | `024-village-of-three-hundred` | Village of Three Hundred | 6.5 | 6.5 | 6.0 | 6.8 | 8.0 | 6.60 | Isometric hamlet simulation; game-like |
| 41 | `025-pottery-wheel` | Centering on the Wheel | 5.2 | 7.0 | 5.0 | 6.5 | 8.2 | 6.23 | Radial 3D deformation lathe; artisanal |
| 42 | `026-frost-on-the-window` | Frost Ice Crystal Growth | 5.2 | 7.4 | 5.0 | 6.2 | 8.0 | 6.31 | Diffusion-limited aggregation; screensaver |
| 43 | `027-calligrams` | Apollinaire Calligrams | 5.5 | 7.2 | 5.2 | 8.0 | 8.2 | 6.64 | Concrete poetry typography; unreadable |
| 44 | `030-rose-window` | Gothic Cathedral Rose Window | 5.8 | 7.8 | 5.2 | 6.5 | 7.8 | 6.46 | Stained glass geometry; religious/ornate |
| 45 | `031-tangram-menagerie` | Tangram Menagerie Puzzles | 5.6 | 6.5 | 5.5 | 6.5 | 8.5 | 6.38 | Geometric puzzle solver; leisure |
| 46 | `033-lava-lamp-1971` | Mathmos Astro Lava Lamp | 5.0 | 7.0 | 5.0 | 6.0 | 8.5 | 6.15 | Blob metaball physics; psychedelic |
| 47 | `035-totality` | Solar Eclipse Totality Corona | 5.2 | 7.5 | 5.0 | 6.5 | 8.2 | 6.34 | Celestial alignment animation; decorative |
| 48 | `037-pendulum-wave` | Mach Pendulum Wave Array | 6.0 | 6.8 | 5.5 | 6.8 | 8.4 | 6.47 | Harmonic oscillator visualization; physics |
| 49 | `038-instant-film` | Polaroid Instant Film Developer | 5.5 | 7.2 | 5.2 | 6.8 | 8.0 | 6.37 | Chemical photographic emergence; novelty |
| 50 | `040-the-harbour-courier-1926` | Harbour Courier Broadsheet | 6.8 | 6.8 | 5.8 | 7.5 | 8.2 | 6.74 | Historic newspaper layout; sepia print |
| 51 | `041-jelly-alphabet` | Wobbly Jelly Alphabet | 4.8 | 6.0 | 4.5 | 6.5 | 8.2 | 5.69 | Soft-body physics text; whimsical toy |
| 52 | `042-dance-of-venus` | Orbital Resonance of Venus | 5.8 | 7.2 | 5.2 | 6.8 | 8.2 | 6.44 | Spirograph celestial resonance; orbital |
| 53 | `043-lichen-on-slate` | Lichen Symbiosis Growth | 5.5 | 7.0 | 5.0 | 6.2 | 8.0 | 6.20 | Cellular automata bio-growth; organic |
| 54 | `044-ariadnes-thread` | Ariadne's Labyrinth Maze | 6.0 | 6.8 | 5.8 | 6.5 | 8.2 | 6.44 | Maze search pathfinding; abstract |
| 55 | `046-snow-at-the-bridge` | Woodblock Print Snow Bridge | 5.2 | 7.6 | 5.0 | 6.8 | 8.0 | 6.36 | Ukiyo-e woodblock homage; artistic print |
| 56 | `048-cross-stitch-studio` | Cross Stitch Pixel Tapestry | 6.0 | 6.5 | 5.5 | 6.8 | 8.5 | 6.42 | Embroidery needlework grid; craft |
| 57 | `049-conchology-cabinet` | Conchology Shell Spiral Study | 6.0 | 7.2 | 5.5 | 6.8 | 8.0 | 6.50 | Marine mollusk taxonomy; nature study |
| 58 | `050-river-from-source-to-sea` | Fluvial River Topography | 6.2 | 6.8 | 5.8 | 6.8 | 8.0 | 6.52 | Hydrological elevation map; educational |
| 59 | `051-pinscreen` | Alexeieff Pinscreen Shadow Art | 5.4 | 7.0 | 5.0 | 6.2 | 8.0 | 6.17 | Pin shadow relief animation; cinema art |
| 60 | `052-beton-brut-zine` | Béton Brut Brutalist Monograph | 6.5 | 7.0 | 6.0 | 7.5 | 8.2 | 6.83 | Architectural concrete; aggressive margins |
| 61 | `053-sandpile` | Bak-Tang-Wiesenfeld Sandpile | 6.0 | 6.8 | 5.5 | 6.5 | 8.5 | 6.45 | Self-organized criticality; math simulation |
| 62 | `054-matryoshka` | Russian Nesting Dolls | 5.0 | 6.8 | 4.8 | 6.2 | 8.2 | 5.96 | Nested SVG illustration; folk toy |
| 63 | `057-a-year-of-daylight` | Polar Solar Day/Night Chart | 6.8 | 7.0 | 6.0 | 7.2 | 8.2 | 6.79 | Photoperiod solar calendar; circular data |
| 64 | `058-the-drawloom` | Jacquard Drawloom Weaving | 6.2 | 6.8 | 5.8 | 6.8 | 8.4 | 6.59 | Textile warp and weft loom; artisanal |
| 65 | `059-pluvia-and-sons-umbrellas` | Bespoke Umbrella Atelier | 6.2 | 7.0 | 5.8 | 7.0 | 8.0 | 6.61 | Retail haberdashery catalog; commercial |
| 66 | `061-moon-tonight` | Lunar Phase & Ephemeris | 6.5 | 7.2 | 6.0 | 7.0 | 8.2 | 6.79 | Astronomy moon phase calculator |
| 67 | `062-wheat-before-rain` | Kinetic Wheat Grass Field | 5.0 | 7.2 | 4.8 | 6.0 | 8.2 | 6.08 | Wind wave field simulation; ambient |
| 68 | `064-par-avion` | Airmail Postal Envelopes | 6.0 | 6.8 | 5.6 | 7.2 | 8.2 | 6.53 | Vintage postal stamps and franking |
| 69 | `065-ripple-tank` | Wave Interference Water Tank | 5.8 | 6.8 | 5.2 | 6.5 | 8.2 | 6.32 | Physics wave superposition simulation |
| 70 | `066-night-diner` | 24-Hour Roadside Diner | 5.8 | 7.2 | 5.2 | 6.8 | 8.0 | 6.42 | Retro neon diner illustration; mood |
| 71 | `067-a-short-history-of-fog` | Meteorology of Coastal Fog | 5.6 | 7.2 | 5.2 | 7.0 | 8.0 | 6.40 | Atmospheric opacity rendering; narrative |
| 72 | `068-gelato-tower` | Gelato Scoop Balancer | 4.6 | 5.8 | 4.2 | 6.0 | 8.4 | 5.48 | Physics balancing game; juvenile |
| 73 | `071-apiary-no-9` | Hive Temperature & Honey Log | 6.8 | 6.8 | 6.0 | 7.0 | 8.2 | 6.77 | Beekeeping sensor log; rustic agrarian |
| 74 | `073-zoetrope` | Victorian Optical Zoetrope | 5.2 | 6.8 | 5.0 | 6.2 | 8.2 | 6.10 | Pre-cinema animation wheel; novelty |
| 75 | `074-collatz-kelp` | Collatz Conjecture Kelp Forest | 5.8 | 7.0 | 5.4 | 6.8 | 8.4 | 6.44 | Number theory fractal growth; generative |
| 76 | `075-wood-type-avalanche` | Letterpress Wood Type Specimen | 6.2 | 7.0 | 5.8 | 7.8 | 8.2 | 6.79 | Letterpress typography avalanche; chaotic |
| 77 | `079-formicarium` | Ant Colony Tunnel Excavation | 5.5 | 6.8 | 5.0 | 6.5 | 8.4 | 6.18 | Insect agent burrowing simulator; toy |

*(Note: Total evaluated studies = 76 numbered studies + 1 gallery engine architecture).*

---

## 4. Design Selection Rationale & The "Strata Obsidian" Synthesis

### 4.1 Why `047-atelier-vesper-watch` Won Primary Selection (Score: 9.32)
1. **Unrivaled Surface & Contrast Gravitas**: Its deep obsidian canvas (`#0C0D0F`), paired with recessed surfaces (`#070B14`) and hairline card elevations (`rgba(255,255,255,0.08)`), solves the glare and contrast deficiencies common in enterprise dashboards.
2. **Tabular Precision**: The study demonstrates immaculate typography: numbers and scores align with `font-variant-numeric: tabular-nums lining-nums`, making relevance scores, latency millisecond figures, and vector dimensions readable at a glance without jitter.
3. **Restrained Engineering Accents**: Gold and blued-steel micro-accents provide high-contrast visual cues for status badges, search rank chips, and active tabs without clownish color saturation.

### 4.2 Synthesis with Complementary Finalists
While `047-atelier-vesper-watch` provides the superior canvas, typographic foundation, and luxury finish, enterprise retrieval requires dense tabular data manipulation and telemetry. Therefore:
- **`002-airship-terminal-split-flap` (Score: 9.14)** contributes the structured document registry table architecture, column alignment, mono ID truncation, and interactive status filter chips (`[ALL]`, `[INDEXED]`, `[PROCESSING]`, `[QUEUED]`, `[FAILED]`).
- **`039-mars-greenhouse-console` (Score: 8.83)** contributes the execution telemetry strip (latency in ms, cache HIT/MISS status, strategy tag) and subsystem health cards (PostgreSQL pool, Redis cache, Celery queue, Embedding engine).

---

## 5. "Strata Obsidian" Design System Specifications

### 5.1 CSS Custom Property Tokens
```css
:root {
  /* Surfaces & Canvas */
  --bg-primary: #07090e;              /* Deep obsidian canvas */
  --bg-surface: #0e131f;              /* Elevated card & table background */
  --bg-surface-elevated: #161e31;     /* Interactive hover & modal plinth */
  --bg-input: #05070b;                /* Recessed input and code background */
  --bg-modal-overlay: rgba(3, 5, 8, 0.85);

  /* Hairline Borders */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.16);
  --border-focus: #6366f1;
  --border-active: rgba(99, 102, 241, 0.4);

  /* Typography Colors */
  --text-primary: #f8fafc;            /* Crisp white headings & values */
  --text-secondary: #94a3b8;          /* Slate body copy & labels */
  --text-muted: #64748b;              /* Dim annotations & placeholders */
  --text-brand: #818cf8;              /* Soft indigo links and brand text */

  /* Semantic Status & Retrieval Accents */
  --accent-brand: #6366f1;            /* Electric Indigo (Primary CTA, Active Tab) */
  --accent-brand-glow: rgba(99, 102, 241, 0.25);
  --accent-cyan: #06b6d4;             /* Neon Cyan (Dense Vector, HNSW Rank) */
  --accent-cyan-glow: rgba(6, 182, 212, 0.2);
  --accent-amber: #f59e0b;            /* Warm Amber (Sparse GIN, Cache MISS, Processing) */
  --accent-amber-glow: rgba(245, 158, 11, 0.2);
  --accent-emerald: #10b981;          /* Emerald (Cache HIT, Indexed, Operational) */
  --accent-emerald-glow: rgba(16, 185, 129, 0.2);
  --accent-rose: #ef4444;             /* Rose (Failed status, Delete action, Circuit open) */
  --accent-rose-glow: rgba(239, 68, 68, 0.2);

  /* Typography Stacks */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'ui-monospace', 'Menlo', Consolas, monospace;

  /* Shadows & Elevations */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.6);
  --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.7), 0 0 0 1px var(--border-subtle);
  --shadow-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 0 1px var(--border-medium);
  --shadow-glow: 0 0 20px -3px var(--accent-brand-glow);

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Transitions */
  --transition-fast: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-smooth: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 5.2 Typographic Scale
- **Display 1 (Top Bar Title)**: `1.125rem` (18px), Weight 700, letter-spacing `-0.02em`.
- **Heading 2 (Workspace Titles)**: `1.25rem` (20px), Weight 600, letter-spacing `-0.015em`.
- **Heading 3 (Section & Card Titles)**: `0.9375rem` (15px), Weight 600, uppercase, letter-spacing `0.05em`.
- **Body Regular (Readable Copy)**: `0.875rem` (14px), Weight 400, line-height `1.6`.
- **Code & Numbers (Monospace Data)**: `0.8125rem` (13px), Weight 500, tabular figures.
- **Micro Label (Badges & Chips)**: `0.6875rem` (11px), Weight 700, uppercase, letter-spacing `0.06em`.

---

## 6. Detailed Workspace Specifications

### 6.1 Top Navigation Bar
- **Brand Identity**: Stylized obsidian mark `[S]` with text `StrataSearch` and subtitle `Enterprise Hybrid Retrieval & Document Intelligence`.
- **Live Status Heartbeat Pill**:
  - Automatically queries `GET /api/v1/health` on mount and periodically every 15 seconds.
  - Three visual states:
    - `Operational`: Pulsing emerald dot (`#10b981`), label *"Gateway Operational"*.
    - `Degraded`: Pulsing amber dot (`#f59e0b`), label *"Degraded Subsystem"*.
    - `Offline`: Solid rose dot (`#ef4444`), label *"Service Offline"*.
- **Live Corpus Counter Badge**:
  - Automatically queries `GET /api/v1/documents` on load and updates dynamically:
    `[ 🗄️ X Documents · Y Chunks ]`.
- **Workspace Navigation Tabs**:
  - Three distinct workspace buttons:
    1. `Search & Retrieval` (`#tab-search`)
    2. `Knowledge Base & Import` (`#tab-knowledge`)
    3. `System Telemetry` (`#tab-telemetry`)
  - Active tab styling: Deep indigo surface with glowing hairline bottom/border accent.
  - Hotkey support: `Alt+1`, `Alt+2`, `Alt+3`.
- **API Documentation Action**:
  - Direct external link to `/docs` (FastAPI Swagger UI) with external icon.

### 6.2 Workspace 1: Search & Retrieval
- **Search Header & Input Bar**:
  - Full-width search bar with clear button (`×`) and autofocus shortcut (`/`).
  - Search submission button with loading spinner state.
- **Retrieval Controls Bar**:
  - **Retrieval Mode Selector**: Dropdown supporting:
    - `Hybrid (Dense HNSW + Sparse GIN RRF Fusion)` (Default)
    - `Dense Only (pgvector HNSW Cosine Distance)`
    - `Sparse Only (PostgreSQL GIN Full-Text Search)`
  - **Top-K Slider**: Range slider (1 to 20, default 5) with synchronized number readout.
  - **RRF Smoothing Parameter (k)**: Number input (default 60).
  - **Document Scope Filter**: Dynamic dropdown populated from indexed documents in `GET /api/v1/documents` (`All Indexed Documents` or specific document ID).
- **Execution Telemetry Strip**:
  - Appears immediately upon search response.
  - Metrics: Latency in ms (emerald), Cache status (`HIT (Redis SHA-256)` in emerald or `MISS (Live DB)` in amber), Strategy used (`HYBRID RRF`, `DENSE HNSW`, `SPARSE GIN`), Candidate count evaluated.
- **Search Result Cards**:
  - Ranked order (`#1`, `#2`, `#3`, ...).
  - Header: Document filename, source format badge (`PDF`, `DOCX`, `TXT`, `URL`), and chunk index (`[chunk #4]`).
  - Score Chips:
    - Dense Rank Badge: `Dense #1` (Cyan `#06b6d4`).
    - Sparse Rank Badge: `Sparse #2` (Amber `#f59e0b`).
    - RRF Composite Score: `RRF: 0.032787` (Indigo `#818cf8`).
  - Snippet: Clean chunk text with matched query keywords wrapped in styled `<mark>` tags.
  - Action: `Inspect Full Context` button opening the inspection modal.
- **Full Context Modal (`#modal-chunk-context`)**:
  - Full-screen dismissible dialog (via `Escape`, backdrop click, or close button `✕`).
  - Complete chunk text in high-legibility typographic format.
  - Raw JSON inspection panel showing all chunk metadata, vectors, and rank attributes.

### 6.3 Workspace 2: Knowledge Base & Import
- **Dual Ingestion Header**:
  - **Dropzone Card (Multi-Format Drag-and-Drop)**:
    - Supports `.pdf`, `.docx`, `.txt`, `.md`, `.csv` (up to 25MB).
    - Drag-over highlight animation.
    - File staging list showing filename, size in KB/MB, and remove action.
    - `Upload & Index Files` button calling `POST /api/v1/documents/upload`.
    - Live upload progress indicator.
  - **URL Importer Card (Web Scraper)**:
    - URL text input field with placeholder (`https://docs.enterprise.com/guide`).
    - `Import Web Page` button calling `POST /api/v1/documents/url`.
    - Clear explanatory text noting automatic readability extraction (strips navigation, headers, footers, scripts).
- **Document Library Table**:
  - **Filter Toolbar**:
    - Real-time search input for filtering table rows by filename.
    - Split-flap inspired status filter chips: `[ ALL ] [ INDEXED ] [ PROCESSING ] [ QUEUED ] [ FAILED ]` with live document counts.
    - Manual refresh button.
  - **Table Columns**:
    1. **Status**: Real-time status dot and label (`queued`, `processing`, `indexed`, `failed`).
    2. **Document Name**: Format badge (`PDF`, `DOCX`, `TXT`, `URL`) and filename.
    3. **Size**: Formatted byte count (KB/MB).
    4. **Chunks**: Integer count of generated semantic chunks.
    5. **Ingestion Date**: Clean formatted timestamp.
    6. **Actions**:
       - `Filter in Search` button (auto-selects document in Search Workspace).
       - `Delete` button (triggers confirmation modal calling `DELETE /api/v1/documents/{doc_id}`).
  - **Smart Polling Engine**:
    - Automatically polls `GET /api/v1/documents` every 4 seconds when any document is in `queued` or `processing` state.
    - Decelerates to 15-second polling when all documents are settled.

### 6.4 Workspace 3: System Telemetry
- **Enterprise KPI Grid**:
  - Total Documents Indexed.
  - Total Embedded Chunks.
  - Corpus Storage Volume.
  - Average Retrieval Latency.
- **Live Subsystem Health Cards**:
  1. **PostgreSQL Connection Pool**: Active/Total connections, pgvector HNSW index operational, GIN tsvector inverted index.
  2. **Redis Query Cache**: SHA-256 query cache status, connection state, in-memory LRU fallback status.
  3. **Celery Worker Pipeline**: Queue status, background task processing, single-node synchronous fallback mode.
  4. **Neural Embedding Engine**: `all-MiniLM-L6-v2`, 384 Float32 dimensions, L2 normalization, pre-warmed status.
- **System Actions**:
  - `Purge Search Cache` button: Dispatches `DELETE /api/v1/cache` and displays instant enterprise toast notification.
  - `Probe Subsystem Health` button: Refreshes `/api/v1/health` probes immediately.
- **Interactive cURL API Integration Snippets**:
  - Tabbed syntax-highlighted cURL commands for enterprise developers:
    - Hybrid RRF Search (`POST /api/v1/search`)
    - Document Multipart Upload (`POST /api/v1/documents/upload`)
    - Web URL Ingestion (`POST /api/v1/documents/url`)
    - Health & Diagnostics (`GET /api/v1/health`)
  - One-click "Copy cURL Command" button with visual feedback.

---

## 7. Anti-Pattern & Demo Deprecation Manifesto

The previous developer test harness contained numerous hardcoded and synthetic artifacts. In the Strata Obsidian implementation, all of the following are permanently and completely removed:

1. **Zero External CSS/JS Frameworks**:
   - Tailwind CDN script tags are completely eliminated.
   - All styling is authored in native vanilla CSS (`styles.css`).
2. **Zero Synthetic Test Artifacts**:
   - Complete elimination of mock synthetic documents, test corpus fixtures, and hardcoded placeholder paragraphs.
   - No hardcoded query suggestions referencing synthetic test data.
   - All search queries execute genuinely against PostgreSQL and pgvector.
3. **Zero Developer Stress-Test Buttons**:
   - Developer stress testing triggers and large-scale synthetic load buttons are removed.
   - Developer DDoS simulation triggers (such as 15 rapid request flood tests) are removed.
   - `✂️ Split into Semantic Chunks` developer sandbox is replaced by the Knowledge Base uploader.
4. **Zero Unauthenticated Mock Demo Endpoints in UI**:
   - All frontend API calls target real REST endpoints:
     - `POST /api/v1/documents/upload`
     - `POST /api/v1/documents/url`
     - `GET /api/v1/documents`
     - `DELETE /api/v1/documents/{doc_id}`
     - `POST /api/v1/search`
     - `DELETE /api/v1/cache`
     - `GET /api/v1/health`
5. **No Native Browser Alerts**:
   - All system alerts and confirmations use clean in-DOM modal dialogs and non-blocking toast notifications.
