import { HtmlSnippetBlock } from './HtmlSnippetBlock';

export interface FindingElement {
  selector?: string | null;
  html_snippet?: string | null;
  location?: string | null;
}

interface FindingElementsListProps {
  elements: FindingElement[] | undefined;
  /** Cap the visible list. Audits commonly attach 5-10 elements per finding;
   * surfacing more would dwarf the surrounding card. Default mirrors the
   * PDF's "showing N of M" pattern from QW3. */
  maxVisible?: number;
}

/**
 * Renders the per-element drill-down attached to a finding by the auditor
 * layer (Workstream A QW1-QW4). Each element shows its landmark-aware
 * location, CSS selector, and HTML snippet. Returns null when there are no
 * elements — callers can render unconditionally.
 *
 * Backend element shape (from utils.make_element_entry + axe adapter):
 *   { selector: string, html_snippet: string, location: string }
 * All three keys may be missing or null on a per-element basis (e.g. when
 * a check captures location but no selector); render only what's present.
 */
export function FindingElementsList({
  elements,
  maxVisible = 10,
}: FindingElementsListProps) {
  if (!elements || elements.length === 0) {
    return null;
  }

  const visible = elements.slice(0, maxVisible);
  const hiddenCount = Math.max(0, elements.length - maxVisible);

  return (
    <div className="mt-3 pt-3 border-t border-dashed border-border space-y-3">
      {visible.map((el, i) => (
        <div key={i} className="space-y-1.5">
          {el.location && (
            <div className="text-[10px] text-text-muted uppercase tracking-wide font-semibold">
              {el.location}
            </div>
          )}
          {el.selector && (
            <code
              className="block text-[11px] font-mono text-text-secondary break-all"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              {el.selector}
            </code>
          )}
          {el.html_snippet && <HtmlSnippetBlock html={el.html_snippet} />}
        </div>
      ))}
      {hiddenCount > 0 && (
        <div className="text-[11px] text-text-muted italic">
          + {hiddenCount} more affected element{hiddenCount === 1 ? '' : 's'}
        </div>
      )}
    </div>
  );
}
