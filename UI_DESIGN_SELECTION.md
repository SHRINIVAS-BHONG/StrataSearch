# StrataSearch UI Design Selection & Design System Specification
**Document Version**: 3.0.0  
**Target Platform**: StrataSearch Enterprise Hybrid Retrieval & Document Intelligence  
**Design System Standard**: *Strata Obsidian — Executive Intelligence Edition*  
**Reference Repository**: `https://github.com/SHRINIVAS-BHONG/Claude-Fable-5.2-HTML-Files`  

---

## 1. Executive Summary

StrataSearch is transitioning from an internal developer test harness to a commercial, client-ready, deployable Enterprise Hybrid Retrieval & Document Intelligence Platform. Developer test harnesses typically feature unstyled form inputs, raw cartoon emojis, synthetic demo text, hardcoded sample paragraphs, and fragile external CDN dependencies.

To establish an authoritative, executive-grade visual identity, an exhaustive survey of all 76 standalone web application studies in `https://github.com/SHRINIVAS-BHONG/Claude-Fable-5.2-HTML-Files` was conducted. Based on a weighted multi-criteria rubric tailored for high-density enterprise software:

1. **`047-atelier-vesper-watch` (Score: 9.32 / 10.0)** was selected as the **primary visual design foundation**. Its deep jeweller's obsidian canvas (`#08090C`, `#0E1219`, `#151B26`), specular hairline border precision (`inset 0 1px 0 rgba(255, 255, 255, 0.08)`), and tabular lining typography (`font-variant-numeric: tabular-nums lining-nums`) provide the luxury mechanical finish and contrast balance demanded by enterprise AI platforms.
2. **`002-airship-terminal-split-flap` (Score: 9.14 / 10.0)** was selected for the **Document Registry table and status management**. It provides the tactile status filter chips (`ALL`, `INDEXED`, `PROCESSING`, `QUEUED`, `FAILED`), glowing signal lamps (`.status-dot` with emerald, amber, and rose halos), and expandable manifest inspection drawers.
3. **`039-mars-greenhouse-console` (Score: 8.83 / 10.0)** was selected for **Real-Time Telemetry and Health Instrumentation**. It provides the sticky execution telemetry strip (live query latency in ms, cache HIT/MISS status, strategy badge) and the 4 subsystem health cards (PostgreSQL 16, Redis Cache, Celery Queue, Embedding Engine).
4. **`045-foundry-specimen-halden` & `014-ulam-prime-spiral`** contribute the **Swiss Modernist typography and control ergonomics**. They provide the clean 12-column grid, segmented retrieval mode switcher, custom precision range slider with live numeric display, and glowing focus rings.
5. **`index.html` (Claude Fable Gallery Engine)** contributes the **Search Toolbar and Card Architecture**. It provides the backdrop-filtered search header, live corpus counter pill, ranked citation cards with numbered rank badges (`#1`, `#2`), and the full-context inspection modal.

The synthesized design system—**Strata Obsidian — Executive Intelligence Edition**—is implemented entirely in pure semantic HTML5, modern CSS3 variables, and vanilla ES6+ JavaScript, with **zero external frameworks** (no Tailwind CDN, no Bootstrap) and **zero emojis** (all replaced with bespoke inline SVG vector icons).

---

## 2. Evaluation Methodology & 5-Dimension Rubric

Every study in `https://github.com/SHRINIVAS-BHONG/Claude-Fable-5.2-HTML-Files` was evaluated across five strict dimensions weighted specifically for high-throughput enterprise developer and data platforms:

| Dimension | Weight | Evaluation Criteria |
|---|---|---|
| **Information Architecture & Density (IA)** | 25% | Organization of dense technical data, tabular status lists, parameter controls, filter facets, and modal drawers without visual clutter or awkward whitespace. |
| **Enterprise Visual Polish & Aesthetics (EVP)** | 25% | Visual gravitas suitable for enterprise software (modern dark theme, high contrast ratio, restrained hairline borders, absence of whimsical, skeuomorphic, or juvenile artifacts). |
| **Component Adaptability for Requirement R5 (CA)** | 25% | Ease of adapting layout patterns into search inputs, multi-attribute rank cards, drag-and-drop dropzones, document status tables, KPI grids, and inspector modals. |
| **Typography & Readability (TH)** | 15% | Dual-font typography hierarchy combining high-legibility geometric sans-serif for body text with tabular lining monospace for scores, latencies, IDs, and cURL snippets. |
| **Zero-Framework Feasibility & Performance (ZFP)** | 10% | Clean vanilla CSS layout mechanics (Flexbox, CSS Grid, Custom Properties) operating without canvas/WebGL frame locks, audio synthesis overhead, or layout thrashing. |

### Weighted Score Formula
$$\text{Score} = (0.25 \times \text{IA}) + (0.25 \times \text{EVP}) + (0.25 \times \text{CA}) + (0.15 \times \text{TH}) + (0.10 \times \text{ZFP})$$

---

## 3. Comprehensive Master Evaluation Matrix (All 76 Templates)

Below is the comprehensive master evaluation matrix covering all 76 studies in `https://github.com/SHRINIVAS-BHONG/Claude-Fable-5.2-HTML-Files` (merging Batch 1 templates 001–035 and Batch 2 templates 036–079):

| Rank | Study ID & Filename | Title / Focus | IA | EVP | CA | TH | ZFP | Score | Key Strengths & Evaluation Summary |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1** | `047-atelier-vesper-watch` | Atelier Vesper — Calibre V.03 | 8.8 | 9.8 | 9.0 | 9.6 | 9.5 | **9.32** | **TOP-RATED WINNER: Primary Visual Design System.** Deep jeweller's obsidian canvas (`#08090C`, `#0E1219`), 1px hairline rules with specular highlights, and tabular lining numerals. Sets the executive tone. |
| **2** | `002-airship-terminal-split-flap` | Aerodrome Lisbeth — Departures | 9.6 | 8.8 | 9.4 | 8.9 | 8.8 | **9.14** | **FINALIST: Tabular Layout & Status Chips.** Dark operational tabular board, split-flap filter chips with counters (`ALL`, `INDEXED`, `PROCESSING`, `QUEUED`, `FAILED`), live glowing signal lamps, and manifest inspection drawers. |
| **3** | `scripts/gallery-template` / `index` | Claude Fable Gallery Engine | 9.0 | 8.6 | 8.9 | 8.8 | 9.8 | **8.93** | **FINALIST: Navigation & Filter Toolbar Engine.** Backdrop-filtered sticky search header, live corpus count badge, card hierarchy with numbered badges (`.num`), format tags, and prompt modal inspector. |
| **4** | `039-mars-greenhouse-console` | ARES-HORT Console Greenhouse B | 9.5 | 7.8 | 9.1 | 8.5 | 9.2 | **8.83** | **FINALIST: Subsystem Telemetry & KPI Cards.** Real-time execution telemetry strip, subsystem health cards with aligned key-value metrics, live status dots, and horizontal bar meters. |
| **5** | `045-foundry-specimen-halden` | Halden Grotesk Type Specimen | 8.2 | 8.5 | 8.2 | 9.5 | 9.0 | **8.58** | **FINALIST: Typographic Grid & Mode Switcher.** Scandinavian modernist grotesque typography, 12-column grid, electric cobalt accents, and segmented view mode buttons (`.modes button`). |
| **6** | `072-lumen-town-grid` | Lumen — Municipal Power Board | 9.0 | 7.2 | 8.5 | 8.2 | 8.9 | **8.35** | High-density municipal telemetry dashboard, header KPI stat row, bordered panels with offset shadows, tabular figures. |
| **7** | `034-museum-of-obsolete-sounds` | Museum of Obsolete Sounds | 8.0 | 8.2 | 7.8 | 8.8 | 8.7 | **8.19** | Immaculate Swiss International Style, stark high contrast, multi-column index sidebar, structured exhibit cards with numbered index badges (`01`, `02`). |
| **8** | `008-cabinet-of-impossible-minerals` | Cabinet of Impossible Minerals | 8.2 | 8.3 | 7.7 | 8.0 | 8.8 | **8.16** | Dark museum showcase theme, modal specimen inspection cards with metadata properties, clean card grid. |
| **9** | `016-vector-lunar-descent` | Descent — Vector Lunar Lander | 8.4 | 7.8 | 7.6 | 8.2 | 8.8 | **8.10** | High-contrast dark terminal theme, vector HUD telemetry (altitude, velocity, fuel remaining), monospace keyboard shortcut badges. |
| **10** | `069-strange-attractors` | Strange Attractors — Orbits | 7.6 | 8.2 | 7.4 | 8.0 | 8.7 | **7.88** | Deep viridian dark canvas, precision mathematical parameter sliders, clean card elevation. |
| 11 | `005-working-slide-rule` | Working Slide Rule Engine | 8.5 | 7.0 | 7.5 | 8.2 | 8.5 | **7.83** | High-precision technical calculation feel, Gill Sans engineering typography; ivory/brass palette is overly skeuomorphic. |
| 12 | `014-ulam-prime-spiral` | Ulam Prime Number Spiral | 7.5 | 7.8 | 7.2 | 8.0 | 8.8 | **7.76** | Pristine Swiss modernism (Helvetica Neue & SF Mono), precision range slider with live readout, filter toggle cards, KPI telemetry readout block. |
| 13 | `029-skerry-weather-station` | Skerry Marine Weather Station | 8.4 | 7.2 | 7.5 | 7.8 | 8.2 | **7.75** | Rich meteorological instrument telemetry, barograph drum, observer log entries; antique brass bezels require modernization. |
| 14 | `055-seismograph-drum` | Seismograph Drum Logger | 8.0 | 7.4 | 7.2 | 7.9 | 8.5 | **7.69** | Tabular disturbance ledger (`<table>` with `tabular-nums lining-nums`), real-time strip chart telemetry, time-series logging. |
| 15 | `019-bauhaus-drum-machine` | Bauhaus Drum Machine | 7.8 | 7.6 | 7.0 | 7.5 | 8.4 | **7.54** | Bauhaus modernist functionalism, Futura typography, 16-step grid sequencer; primary color accents feel retro. |
| 16 | `022-hotel-meridian-elevator` | Hotel Meridian Elevator Bank | 7.9 | 7.3 | 7.1 | 7.6 | 8.5 | **7.53** | Art Deco typography, floor indicator dial, narrative vignettes; limited multi-workspace SaaS application. |
| 17 | `063-the-astrolabe` | The Planispheric Astrolabe | 7.2 | 8.5 | 6.5 | 7.8 | 7.9 | **7.44** | Ornate brass celestial calculator, rotating plates; antique museum aesthetic lacks enterprise SaaS relevance. |
| 18 | `056-the-combination` | The Combination Safe Dial | 7.0 | 7.8 | 6.8 | 7.5 | 8.5 | **7.40** | Mechanical safe dial with tactile haptics; single-dial interaction lacks document data layouts. |
| 19 | `060-ascii-tide` | ASCII Tide Gauge & Moon | 7.6 | 7.0 | 7.0 | 7.9 | 8.5 | **7.43** | Monospace continuous feed printer chart; excellent inspiration for cURL terminal snippets, but too low-fi for main UI. |
| 20 | `011-the-hours-in-words` | The Hours in Words | 6.5 | 7.8 | 6.5 | 8.8 | 8.8 | **7.35** | High-contrast typography, minimalist mode buttons (`plain` vs `elaborate`); single-purpose word clock. |
| 21 | `032-the-night-typist` | The Night Typist Mechanical | 6.8 | 7.5 | 6.5 | 8.2 | 8.4 | **7.32** | Crisp mechanical monospace rendering, red/black ink toggle; vintage typewriter theme unsuited for enterprise search. |
| 22 | `004-lighthouse-keeper-night-watch` | Lighthouse Keeper Night Watch | 7.2 | 7.5 | 6.4 | 7.4 | 8.0 | **7.19** | Atmospheric nighttime marine illustration, quiet logbook; single-narrative storytelling lacks enterprise controls. |
| 23 | `036-kestrel-frameworks-bicycles` | Kestrel Frameworks Bicycles | 7.2 | 7.0 | 6.8 | 7.5 | 8.0 | **7.18** | 4-sheet multi-view navigation, structured specification tables, revision log; blueprint cyanotype styling is domain-specific. |
| 24 | `028-conservas-mare-alta` | Conservas Mare Alta Sardines | 6.8 | 7.4 | 6.2 | 7.6 | 8.2 | **7.11** | Structured product card grid, lot number/weight specifications, modal inspection view; vintage cannery label aesthetic. |
| 25 | `013-iron-filings` | Iron Filings Magnetic Flux | 6.2 | 7.6 | 6.4 | 7.0 | 8.5 | **7.07** | Clean laboratory notebook aesthetic, segmented control buttons; physics magnetic simulation with high GPU overhead. |
| 26 | `015-maison-ombre-perfume` | Maison Ombre Luxury Fragrance | 6.5 | 8.0 | 6.0 | 7.8 | 8.0 | **7.07** | Luxury editorial typography (Didot), chapter navigation bar (`I, II, III`), olfactory pyramid table; overly ornate for B2B SaaS. |
| 27 | `023-walnut-turntable` | Walnut Turntable Vinyl Audio | 6.4 | 7.6 | 6.0 | 7.2 | 8.1 | **6.99** | Mid-century hi-fi audio aesthetic, brushed aluminum styling, speed switches; consumer audio skeuomorphism. |
| 28 | `018-pen-plotter-landscapes` | Pen Plotter Generative Topo | 6.5 | 7.5 | 6.2 | 7.0 | 8.3 | **6.98** | Industrial CNC plotter control panel, aluminum hardware styling, live X/Y coordinate readouts; machinery focus. |
| 29 | `070-semaphore` | Maritime Flag Semaphore | 6.8 | 6.8 | 6.5 | 7.2 | 8.4 | **6.95** | High-contrast mid-century poster style, primary flag signaling; educational novelty toy. |
| 30 | `007-ice-core-800-metres` | Antarctic Ice Core Log | 7.0 | 6.8 | 6.2 | 7.2 | 7.8 | **6.89** | Scientific telemetry aesthetic, cool arctic palette, depth gauge meter, core inspection tool; vertical scroll format. |
| 31 | `052-beton-brut-zine` | Béton Brut Brutalist Monograph | 6.5 | 7.0 | 6.0 | 7.5 | 8.2 | **6.83** | Brutalist monochrome styling, high-contrast raw architectural grid; anti-commercial zine aesthetic. |
| 32 | `057-a-year-of-daylight` | Polar Solar Day/Night Chart | 6.8 | 7.0 | 6.0 | 7.2 | 8.2 | **6.79** | Swiss information design, clean grotesk typography, interactive filter chips, tabular solar calendar. |
| 33 | `061-moon-tonight` | Lunar Phase & Ephemeris | 6.5 | 7.2 | 6.0 | 7.0 | 8.2 | **6.79** | Dark celestial aesthetic (`#0A0A0D`), precision ephemeris dial, gold accents; single-purpose astronomical tool. |
| 34 | `075-wood-type-avalanche` | Letterpress Wood Type Specimen | 6.2 | 7.0 | 5.8 | 7.8 | 8.2 | **6.79** | Printing workshop motif, tactile wood type sorts; physics avalanche is chaotic. |
| 35 | `071-apiary-no-9` | Hive Temperature & Honey Log | 6.8 | 6.8 | 6.0 | 7.0 | 8.2 | **6.77** | Amber/wax color palette, structured sensor log; consumer e-commerce landing page. |
| 36 | `040-the-harbour-courier-1926` | Harbour Courier Broadsheet | 6.8 | 6.8 | 5.8 | 7.5 | 8.2 | **6.74** | Multi-column broadsheet layout, tabular shipping ledger; 1920s newspaper period styling with aged paper background. |
| 37 | `010-op-art-pulse` | Op Art Optical Pulse | 5.8 | 7.5 | 5.8 | 6.5 | 8.8 | **6.68** | Monochrome geometric styling, clean navigation links; abstract optical flicker induces eye fatigue. |
| 38 | `001-suminagashi-marbling-tray` | Suminagashi Water Marbling | 5.5 | 7.8 | 5.5 | 6.8 | 8.2 | **6.67** | Smooth fluid canvas physics, elegant Japanese color palette; purely artistic toy simulation with zero data UI. |
| 39 | `003-anatomy-of-a-croissant` | Anatomy of a Croissant | 6.5 | 6.8 | 5.8 | 7.2 | 8.2 | **6.65** | Refined editorial typography, ingredient proportion data table; warm culinary magazine theme unsuited for SaaS. |
| 40 | `021-drawer-of-imaginary-moths` | Drawer of Imaginary Moths | 6.2 | 7.4 | 5.8 | 6.8 | 8.0 | **6.64** | Clean specimen card taxonomy, Latin naming typography, inspection loupe; Victorian museum cabinet aesthetic. |
| 41 | `027-calligrams` | Apollinaire Calligrams | 5.5 | 7.2 | 5.2 | 8.0 | 8.2 | **6.64** | Top Roman numeral navigation pills, Baskerville typography; concrete poetry showcase with no data features. |
| 42 | `006-volcan-chico-hot-sauce` | Volcán Chico Hot Sauce | 6.0 | 7.0 | 6.0 | 7.0 | 8.2 | **6.62** | Vibrant product card layout, spice-level pairing selector; fast-food consumer retail aesthetic clashes with B2B. |
| 43 | `059-pluvia-and-sons-umbrellas` | Bespoke Umbrella Atelier | 6.2 | 7.0 | 5.8 | 7.0 | 8.0 | **6.61** | Professional dark slate palette, structured specification tables, product cards; retail haberdashery focus. |
| 44 | `024-village-of-three-hundred` | Village of Three Hundred | 6.5 | 6.5 | 6.0 | 6.8 | 8.0 | **6.60** | Clean demographic card grid, relationship badges, data attributes; folkloric village simulation lacks corporate polish. |
| 45 | `058-the-drawloom` | Jacquard Drawloom Weaving | 6.2 | 6.8 | 5.8 | 6.8 | 8.4 | **6.59** | Textile draft diagram, punch-card pattern editor, linen paper styling; specialized historic craft interface. |
| 46 | `064-par-avion` | Airmail Postal Envelopes | 6.0 | 6.8 | 5.6 | 7.2 | 8.2 | **6.53** | Kraft-paper airmail stationery aesthetic, postage stamps, timeline tracking; inappropriate for document intelligence. |
| 47 | `017-spore-print-riso-zine` | Spore Print Risograph Zine | 6.0 | 6.8 | 5.8 | 7.0 | 8.2 | **6.52** | Creative Risograph layered print styling, paper texture; fluorescent DIY zine aesthetic is non-corporate. |
| 48 | `050-river-from-source-to-sea` | Fluvial River Topography | 6.2 | 6.8 | 5.8 | 6.8 | 8.0 | **6.52** | Continuous horizontal scroll, illustrated narrative journey; children's book/folk art aesthetic. |
| 49 | `049-conchology-cabinet` | Conchology Shell Spiral Study | 6.0 | 7.2 | 5.5 | 6.8 | 8.0 | **6.50** | Specimen grid layout, parametric 3D shell mathematics; shell-pink plaster gallery aesthetic is too delicate. |
| 50 | `037-pendulum-wave` | Mach Pendulum Wave Array | 6.0 | 6.8 | 5.5 | 6.8 | 8.4 | **6.47** | Precision harmonic physics simulation, brass dials; museum vitrine aesthetic with zero search relevance. |
| 51 | `030-rose-window` | Gothic Cathedral Rose Window | 5.8 | 7.8 | 5.2 | 6.5 | 7.8 | **6.46** | Intricate gothic radial geometry, time-of-day solar lighting controls; religious architecture simulation. |
| 52 | `012-murmuration-at-dusk` | Starling Murmuration Flight | 5.4 | 7.6 | 5.2 | 6.5 | 8.2 | **6.45** | Serene dusk color palette, fluid boids flocking particle physics; purely decorative background simulation. |
| 53 | `053-sandpile` | Bak-Tang-Wiesenfeld Sandpile | 6.0 | 6.8 | 5.5 | 6.5 | 8.5 | **6.45** | 4-color screenprint look, self-organized criticality simulation; minimal UI controls, zero data management. |
| 54 | `042-dance-of-venus` | Orbital Resonance of Venus | 5.8 | 7.2 | 5.2 | 6.8 | 8.2 | **6.44** | Classical celestial orbital mechanics, antique parchment motif; academic astronomy with no SaaS utility. |
| 55 | `044-ariadnes-thread` | Ariadne's Labyrinth Maze | 6.0 | 6.8 | 5.8 | 6.5 | 8.2 | **6.44** | Attic black-figure pottery motif, procedural labyrinth pathfinding; ancient terracotta art style. |
| 56 | `074-collatz-kelp` | Collatz Conjecture Kelp Forest | 5.8 | 7.0 | 5.4 | 6.8 | 8.4 | **6.44** | Marine teal/orange aesthetic, tree graph visualization, dive-gauge status dials; aquarium simulation theme. |
| 57 | `048-cross-stitch-studio` | Cross Stitch Pixel Tapestry | 6.0 | 6.5 | 5.5 | 6.8 | 8.5 | **6.42** | Grid-based canvas drawing, color palette picker; textile embroidery craft theme has zero SaaS relevance. |
| 58 | `066-night-diner` | 24-Hour Roadside Diner | 5.8 | 7.2 | 5.2 | 6.8 | 8.0 | **6.42** | Late-night roadside diner diorama, neon lighting effects; nostalgic americana scene without software utility. |
| 59 | `067-a-short-history-of-fog` | Meteorology of Coastal Fog | 5.6 | 7.2 | 5.2 | 7.0 | 8.0 | **6.40** | Editorial long-form article layout, quiet maritime palette; magazine reading format lacks dynamic controls. |
| 60 | `009-koi-pond-noon` | Koi Pond Noon Shimmer | 5.2 | 7.5 | 5.2 | 6.2 | 8.4 | **6.39** | Tranquil ambient canvas ripples and koi animation; purely decorative visual demo with no software utility. |
| 61 | `031-tangram-menagerie` | Tangram Menagerie Puzzles | 5.6 | 6.5 | 5.5 | 6.5 | 8.5 | **6.38** | Interactive SVG polygon dragging and snapping; geometric toy puzzle game without business data controls. |
| 62 | `038-instant-film` | Polaroid Instant Film Developer | 5.5 | 7.2 | 5.2 | 6.8 | 8.0 | **6.37** | Realistic photo developing animations, vintage film aesthetic; whimsical toy camera motif, pastel blush palette. |
| 63 | `046-snow-at-the-bridge` | Woodblock Print Snow Bridge | 5.2 | 7.6 | 5.0 | 6.8 | 8.0 | **6.36** | Japanese ukiyo-e woodblock print aesthetic, subtle falling snow animation; fine art visual study. |
| 64 | `020-aurora-over-the-fjord` | Aurora Over the Fjord | 5.0 | 7.8 | 5.0 | 6.2 | 8.0 | **6.35** | Deep dark night sky palette, smooth multi-pass canvas shader rendering; zero UI components, purely scenic. |
| 65 | `035-totality` | Solar Eclipse Totality Corona | 5.2 | 7.5 | 5.0 | 6.5 | 8.2 | **6.34** | Astronomical contact timeline navigation (`C1`, `C2`, `MAX`), theme transitions; single-narrative timeline scroll. |
| 66 | `065-ripple-tank` | Wave Interference Water Tank | 5.8 | 6.8 | 5.2 | 6.5 | 8.2 | **6.32** | Laboratory instrument layout, numeric tabs (`01`, `02`), telemetry status bar (`.plate`); tank canvas is physics-specific. |
| 67 | `026-frost-on-the-window` | Frost Ice Crystal Growth | 5.2 | 7.4 | 5.0 | 6.2 | 8.0 | **6.31** | Atmospheric winter palette, temperature differential badge; generative canvas frost simulation, screensaver-like. |
| 68 | `025-pottery-wheel` | Centering on the Wheel | 5.2 | 7.0 | 5.0 | 6.5 | 8.2 | **6.23** | Dynamic 3D rotational canvas deformation physics, glaze color selector palette; interactive crafting game. |
| 69 | `043-lichen-on-slate` | Lichen Symbiosis Growth | 5.5 | 7.0 | 5.0 | 6.2 | 8.0 | **6.20** | Subtle dark slate palette, organic time-lapse growth simulation; rock texture, zero enterprise navigation. |
| 70 | `079-formicarium` | Ant Colony Tunnel Excavation | 5.5 | 6.8 | 5.0 | 6.5 | 8.4 | **6.18** | Naturalist field notebook layout, timestamped observation log table; ant colony burrowing simulation. |
| 71 | `051-pinscreen` | Alexeieff Pinscreen Shadow Art | 5.4 | 7.0 | 5.0 | 6.2 | 8.0 | **6.17** | Glossy black acrylic desk toy simulation, 3D surface depth; novelty toy simulation without search utility. |
| 72 | `033-lava-lamp-1971` | Mathmos Astro Lava Lamp | 5.0 | 7.0 | 5.0 | 6.0 | 8.5 | **6.15** | Fluid metabolic blob animation, warm 1970s orange/magenta retro palette; novelty decorative toy. |
| 73 | `073-zoetrope` | Victorian Optical Zoetrope | 5.2 | 6.8 | 5.0 | 6.2 | 8.2 | **6.10** | Victorian parlour optical toy, persistence-of-vision animation, brass/mahogany aesthetic; historic curiosity. |
| 74 | `062-wheat-before-rain` | Kinetic Wheat Grass Field | 5.0 | 7.2 | 4.8 | 6.0 | 8.2 | **6.08** | Full-bleed painted landscape, wind wave field animation; pure digital fine art with zero UI elements. |
| 75 | `054-matryoshka` | Russian Nesting Dolls | 5.0 | 6.8 | 4.8 | 6.2 | 8.2 | **5.96** | Russian folk art illustration, nested SVG animations; ornate floral decoration, completely non-functional for data. |
| 76 | `041-jelly-alphabet` | Wobbly Jelly Alphabet | 4.8 | 6.0 | 4.5 | 6.5 | 8.2 | **5.69** | Soft-body physics, hot pink neon palette (`#FF2E7E`), cartoon jelly styling; interactive toy without enterprise utility. |
| 77 | `068-gelato-tower` | Gelato Scoop Balancer | 4.6 | 5.8 | 4.2 | 6.0 | 8.4 | **5.48** | Pastel arcade ice cream physics game; casual gaming mechanics completely out of enterprise retrieval scope. |

*(Note: Exactly 76 numbered studies exist in the repository spanning files `001` through `079`, plus `index.html` / `gallery-template.html`. Studies `076`, `077`, and `078` are intentionally absent in upstream numbering).*

---

## 4. Design Selection Rationale & The "Strata Obsidian" Synthesis

### 4.1 Why `047-atelier-vesper-watch` Won Primary Selection (Score: 9.32)
1. **Unrivaled Surface & Contrast Gravitas**: Its deep jeweller's obsidian canvas (`#08090C`, `#0E1219`), paired with recessed wells (`#050608`) and specular hairline top-edge highlights (`inset 0 1px 0 rgba(255, 255, 255, 0.08)`), provides pristine readability and eliminates visual fatigue during prolonged retrieval sessions.
2. **Tabular Lining Precision**: The study demonstrates immaculate typography: all metric figures, latency values, chunk counters, and scores align with `font-variant-numeric: tabular-nums lining-nums`, making relevance scores, latency readouts, and vector dimensions readable at a glance without jitter.
3. **Restrained Engineering Accents**: Gold and blued-steel micro-accents provide high-contrast visual cues for status badges, search rank chips, and active tabs without clownish color saturation.

### 4.2 Synthesis with Complementary Finalists
While `047-atelier-vesper-watch` provides the superior canvas, typographic foundation, and luxury finish, enterprise retrieval requires dense tabular data manipulation and telemetry. Therefore:
- **`002-airship-terminal-split-flap` (Score: 9.14)** contributes the structured document registry table architecture, column alignment, mono ID truncation, and interactive status filter chips (`[ALL]`, `[INDEXED]`, `[PROCESSING]`, `[QUEUED]`, `[FAILED]`).
- **`039-mars-greenhouse-console` (Score: 8.83)** contributes the execution telemetry strip (latency in ms, cache HIT/MISS status, strategy tag) and subsystem health cards (PostgreSQL pool, Redis cache, Celery queue, Embedding engine).
- **`045-foundry-specimen-halden` & `014-ulam-prime-spiral`** contribute the clean 12-column grid, segmented retrieval mode switcher, precision range slider with synchronized readouts, and glowing focus rings.
- **`index.html` (Claude Fable Gallery Engine)** contributes the search toolbar, live counter badge, card hierarchy with numbered badges (`#1`, `#2`), and the chunk inspection modal.

---

## 5. "Strata Obsidian — Executive Intelligence Edition" Design Tokens

### 5.1 CSS Custom Property Tokens
```css
:root {
  /* Surfaces & Canvas (Synthesized from 047-atelier-vesper & 002-split-flap) */
  --bg-primary: #08090C;             /* Deep obsidian canvas void */
  --bg-surface: #0E1219;             /* Base elevated card & panel surface */
  --bg-surface-elevated: #151B26;    /* Plinth hover, active tab, and modal surface */
  --bg-surface-subtle: #121721;      /* Intermediate card body / table alternate row */
  --bg-input: #050608;               /* Recessed sunken well for inputs & code blocks */
  --bg-glass: rgba(14, 18, 25, 0.85);/* Frosted glass overlay (with backdrop-filter) */
  --bg-modal-overlay: rgba(4, 5, 8, 0.85); /* High-contrast modal backdrop */

  /* Specular Hairline Borders & Edge Lighting */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.16);
  --border-strong: rgba(255, 255, 255, 0.28);
  --border-focus: #6366F1;           /* Electric Indigo */
  --border-active: rgba(99, 102, 241, 0.40);
  --border-specular: inset 0 1px 0 rgba(255, 255, 255, 0.08);

  /* Typographic Color Hierarchy */
  --text-primary: #F8FAFC;           /* Crisp luminous white for headings and values */
  --text-secondary: #94A3B8;         /* Cool slate for readable body and descriptions */
  --text-muted: #64748B;             /* Dim annotations, table headers, placeholders */
  --text-brand: #818CF8;             /* Soft indigo brand highlight and links */

  /* Semantic State & Retrieval Accents */
  --accent-brand: #6366F1;           /* Electric Indigo (Primary CTA, Active Workspace) */
  --accent-brand-hover: #4F46E5;
  --accent-brand-glow: rgba(99, 102, 241, 0.28);
  --accent-cyan: #06B6D4;            /* Neon Cyan (Dense Vector, HNSW Rank, URL source) */
  --accent-cyan-glow: rgba(6, 182, 212, 0.22);
  --accent-amber: #F59E0B;           /* Signal Amber (Sparse GIN, Cache MISS, Processing) */
  --accent-amber-glow: rgba(245, 158, 11, 0.22);
  --accent-emerald: #10B981;         /* Vivid Emerald (Cache HIT, Indexed, Operational) */
  --accent-emerald-glow: rgba(16, 185, 129, 0.22);
  --accent-rose: #EF4444;            /* Laser Rose (Failed, Invalidate Cache, Delete) */
  --accent-rose-glow: rgba(239, 68, 68, 0.22);

  /* Typography Stacks */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'ui-monospace', 'Menlo', Monaco, Consolas, monospace;

  /* Card Elevations & Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.6);
  --shadow-card: 0 4px 24px -2px rgba(0, 0, 0, 0.70), 0 0 0 1px var(--border-subtle), var(--border-specular);
  --shadow-card-hover: 0 12px 36px -4px rgba(0, 0, 0, 0.85), 0 0 0 1px var(--border-medium), inset 0 1px 0 rgba(255, 255, 255, 0.14);
  --shadow-modal: 0 25px 60px -12px rgba(0, 0, 0, 0.95), 0 0 0 1px var(--border-medium), inset 0 1px 0 rgba(255, 255, 255, 0.12);
  --shadow-glow: 0 0 24px -2px var(--accent-brand-glow);

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
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
- **Brand Identity**: Stylized obsidian geometric monogram with vector layers and clean text `StrataSearch` with subtitle `Enterprise Hybrid Retrieval & Document Intelligence`.
- **Live Status Heartbeat Pill**:
  - Automatically queries `GET /api/v1/health` on mount and periodically every 15 seconds.
  - Three visual states:
    - `Operational`: Pulsing emerald dot (`#10b981`), label *"Gateway Operational"*.
    - `Degraded`: Pulsing amber dot (`#f59e0b`), label *"Degraded Subsystem"*.
    - `Offline`: Solid rose dot (`#ef4444`), label *"Service Offline"*.
- **Live Corpus Counter Badge**:
  - Automatically queries `GET /api/v1/documents` on load and updates dynamically:
    `[ X Documents · Y Chunks ]`.
- **Workspace Navigation Tabs**:
  - Three distinct workspace buttons with inline SVG vector icons:
    1. `Search & Retrieval` (`#tab-search`)
    2. `Knowledge Base & Import` (`#tab-knowledge`)
    3. `System Telemetry` (`#tab-telemetry`)
  - Active tab styling: Deep indigo surface with glowing hairline bottom/border accent.
  - Hotkey support: `Alt+1`, `Alt+2`, `Alt+3`.
- **API Documentation Action**:
  - Direct external link to `/docs` (FastAPI Swagger UI) with external icon.

### 6.2 Workspace 1: Search & Retrieval
- **Search Header & Input Bar**:
  - Full-width search bar with clean inline vector search icon, clear button (`×`), and autofocus shortcut (`/`).
  - Search submission button with rotating vector loading spinner state.
- **Retrieval Controls Bar**:
  - **Retrieval Mode Selector**: Styled select element supporting:
    - `Hybrid (Dense HNSW + Sparse GIN RRF Fusion)` (Default)
    - `Dense Only (pgvector HNSW Cosine Distance)`
    - `Sparse Only (PostgreSQL GIN Full-Text Search)`
  - **Top-K Slider**: Custom sleek range slider (1 to 20, default 5) with synchronized number readout and gradient fill.
  - **RRF Smoothing Parameter (k)**: Number input (default 60).
  - **Document Scope Filter**: Dynamic dropdown populated from indexed documents in `GET /api/v1/documents` (`All Indexed Documents` or specific document ID).
- **Execution Telemetry Strip**:
  - Appears immediately upon search response.
  - Metrics: Latency in ms (emerald), Cache status (`HIT (Redis SHA-256)` in emerald or `MISS (Live DB)` in amber), Strategy used (`HYBRID RRF`, `DENSE HNSW`, `SPARSE GIN`), Candidate count evaluated.
- **Search Result Cards**:
  - Ranked order (`#1`, `#2`, `#3`, ...).
  - Header: Document filename, source format badge (`PDF` in ruby red, `DOCX` in royal blue, `TXT`/`MD` in cool slate, `URL` in neon cyan), and chunk index (`[chunk #4]`).
  - Score Chips:
    - Dense Rank Badge: `Dense #1` (Cyan `#06b6d4`).
    - Sparse Rank Badge: `Sparse #2` (Amber `#f59e0b`).
    - RRF Composite Score: `RRF: 0.032787` (Indigo `#818cf8`).
  - Snippet: Clean chunk text with matched query keywords wrapped in styled `<mark>` tags.
  - Action: `Inspect Full Context` button opening the inspection modal.
- **Full Context Modal (`#modal-chunk-context`)**:
  - Full-screen dismissible dialog (via `Escape`, backdrop click, or close button).
  - Complete chunk text in high-legibility typographic format.
  - Raw JSON inspection panel showing all chunk metadata, vectors, and rank attributes.

### 6.3 Workspace 2: Knowledge Base & Import
- **Dual Ingestion Header**:
  - **Dropzone Card (Multi-Format Drag-and-Drop)**:
    - Supports `.pdf`, `.docx`, `.txt`, `.md`, `.csv` (up to 25MB).
    - Drag-over highlight animation with radial glow.
    - File staging list showing filename, size in KB/MB, and remove action.
    - `Upload & Index Files` button calling `POST /api/v1/documents/upload`.
    - Live animated upload progress bar with gradient shimmer.
  - **URL Importer Card (Web Scraper)**:
    - URL text input field with placeholder (`https://docs.enterprise.com/guide`).
    - `Fetch & Index URL` button calling `POST /api/v1/documents/url`.
    - Clear explanatory text noting automatic readability extraction (strips navigation, headers, footers, scripts).
- **Document Library Table**:
  - **Filter Toolbar**:
    - Real-time search input for filtering table rows by filename.
    - Split-flap inspired status filter chips: `[ ALL ] [ INDEXED ] [ PROCESSING ] [ QUEUED ] [ FAILED ]` with live document counts and embedded glowing status lamps.
    - Manual refresh button with rotating vector indicator.
  - **Table Columns**:
    1. **Status**: Real-time status dot and label (`queued`, `processing`, `indexed`, `failed`).
    2. **Document Name**: Format badge (`PDF`, `DOCX`, `TXT`, `URL`) and filename.
    3. **Size**: Formatted byte count (KB/MB).
    4. **Chunks**: Integer count of generated semantic chunks.
    5. **Indexed Date**: Clean formatted timestamp.
    6. **Actions**:
       - `Filter in Search` button (auto-selects document in Search Workspace).
       - `Delete` button (triggers confirmation modal calling `DELETE /api/v1/documents/{doc_id}`).
  - **Smart Polling Engine**:
    - Automatically polls `GET /api/v1/documents` every 4 seconds when any document is in `queued` or `processing` state.
    - Decelerates to 15-second polling when all documents are settled.

### 6.4 Workspace 3: System Telemetry
- **Enterprise KPI Grid**:
  - 4-card grid:
    1. Total Documents Indexed
    2. Total Embedded Chunks
    3. Corpus Storage Volume
    4. Retrieval Latency Target (< 15 ms)
- **Live Subsystem Health Cards**:
  1. **PostgreSQL Connection Pool**: Active/Total connections, pgvector HNSW index operational, GIN tsvector inverted index.
  2. **Redis Query Cache**: SHA-256 query cache status, connection state, in-memory LRU fallback status.
  3. **Celery Worker Pipeline**: Queue status, background task processing, single-node synchronous fallback mode.
  4. **Neural Embedding Engine**: `all-MiniLM-L6-v2`, 384 Float32 dimensions, L2 normalization, pre-warmed status.
- **System Actions**:
  - `Probe Health` button: Refreshes `/api/v1/health` probes immediately.
  - `Invalidate Cache` button: Dispatches `DELETE /api/v1/cache` and displays instant enterprise toast notification.
- **Interactive cURL API Integration Snippets**:
  - Tabbed syntax-highlighted cURL commands for enterprise developers:
    - Hybrid RRF Search (`POST /api/v1/search`)
    - Document Multipart Upload (`POST /api/v1/documents/upload`)
    - Web URL Ingestion (`POST /api/v1/documents/url`)
    - Health & Diagnostics (`GET /api/v1/health`)
  - One-click "Copy cURL" button with clipboard integration and visual feedback.

---

## 7. Anti-Pattern & Demo Deprecation Manifesto

The previous developer test harness contained numerous hardcoded, emoji-heavy, and synthetic artifacts. In the Strata Obsidian implementation, all of the following are permanently and completely removed:

1. **Zero Raw Emojis**:
   - Every single emoji glyph (`🔍`, `📚`, `⚡`, `🗄️`, `🐘`, `⚙️`, `🧠`, `📥`, `🌐`, `🩺`, `🗑️`, `⏳`, `⚠️`) is completely replaced by clean, modern inline SVG vector icons with consistent 1.5px stroke weight and geometric precision.
2. **Zero External CSS/JS Frameworks**:
   - Tailwind CDN script tags are completely eliminated.
   - All styling is authored in native vanilla CSS (`styles.css`).
3. **Zero Synthetic Test Artifacts**:
   - Complete elimination of mock synthetic documents, test corpus fixtures, and hardcoded placeholder paragraphs.
   - No synthetic `needle_` text (`needle_raft_latency`, `needle_hnsw_ef`, `needle_gin_compaction`).
   - No hardcoded query suggestions referencing synthetic test data.
   - All search queries execute genuinely against PostgreSQL and pgvector.
4. **Zero Developer Stress-Test Buttons**:
   - "Launch 100k Benchmark" and "Fire 15 Rapid Requests" developer stress test buttons are completely removed.
   - `✂️ Split into Semantic Chunks` developer sandbox is replaced by the production Knowledge Base uploader.
5. **Zero Unauthenticated Mock Demo Endpoints in UI**:
   - All frontend API calls target real REST endpoints (`/api/v1/documents/*`, `/api/v1/search`, `/api/v1/cache`, `/api/v1/health`).
6. **No Native Browser Alerts**:
   - All system alerts and confirmations use clean in-DOM modal dialogs and non-blocking toast notifications.
