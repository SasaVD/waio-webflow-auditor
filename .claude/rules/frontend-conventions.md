# Frontend Conventions — WAIO Audit Tool

## Design System (Veza Digital Brand)

### Color Tokens (defined in frontend/src/index.css @theme block)
```
Primary:       #2820FF (CTA, accents, links)
Primary Hover: #1E18CC
Surface:       #FFFFFF (page background)
Surface Secondary: #F7F8FA (card backgrounds)
Surface Dark:  #0F0F14 (dark sections, score gauge bg)
Border:        #E5E7EB
Border Light:  #F0F1F3
Text Primary:  #0F0F14
Text Secondary: #4B5563
Text Muted:    #9CA3AF
```

### Score Colors
```
Excellent (90-100): #22C55E → text-score-excellent
Good (75-89):       #84CC16 → text-score-good
Needs Work (55-74): #EAB308 → text-score-needs
Poor (35-54):       #F97316 → text-score-poor
Critical (0-34):    #EF4444 → text-score-critical
```

### Severity Colors
```
Critical: #EF4444, bg: #FEF2F2
High:     #F97316, bg: #FFF7ED
Medium:   #EAB308, bg: #FEFCE8
```

### Typography
- Font: Inter (loaded from Google Fonts in index.html)
- Weights used: 400, 500, 600, 700, 800, 900

## Component Patterns

### Report Pillar Registration
When adding a new pillar, update ALL of these:

1. `AuditReport.tsx` → `pillarMeta` object:
```tsx
const pillarMeta: Record<string, { icon: any; label: string }> = {
  new_pillar: { icon: SomeIcon, label: 'New Pillar Name' },
};
```

2. `LoadingState.tsx` → `steps` array (add a loading message)

3. `CompetitiveReport.tsx` → reads from `pillar_labels` in report data

4. `SiteAuditReport.tsx` → score display per page

### State Management
- No global state library. Use React state + prop drilling.
- API responses stored in component state via `useState`.
- Loading states tracked per-operation (e.g., `pdfLoading`, `mdLoading`).

### Animation Pattern
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5, delay: 0.1 }}
>
```

### Score Display Pattern
```tsx
const scoreColorClass = (label: string): string => {
  const l = label.toLowerCase();
  if (l === 'excellent') return 'text-score-excellent';
  if (l === 'good') return 'text-score-good';
  if (l === 'needs improvement') return 'text-score-needs';
  if (l === 'poor') return 'text-score-poor';
  return 'text-score-critical';
};
```

### New Component: D3 Link Graph (Sprint 3)
The Obsidian-style network visualization will be a standalone React component:
- Use `d3-force` for the force-directed layout simulation
- Dark background (surface-dark), node colors by topic cluster
- Node size = inbound link count, orphan nodes visually distinct
- Interactive: drag, zoom, hover tooltips, click-to-highlight connections
- Export as static SVG for PDF reports
- Data format:
```json
{
  "nodes": [{"id": "/url", "label": "Page Name", "cluster": 0, "inbound": 12, "depth": 1}],
  "links": [{"source": "/url-a", "target": "/url-b", "anchor": "link text"}]
}
```

## Build Configuration
- Vite 7 with React plugin and TailwindCSS 4 Vite plugin
- TypeScript strict mode enabled
- `noUnusedLocals: true` and `noUnusedParameters: true` — fix warnings before deploy
- Railway runs `tsc -b && vite build` which WILL fail on type errors
