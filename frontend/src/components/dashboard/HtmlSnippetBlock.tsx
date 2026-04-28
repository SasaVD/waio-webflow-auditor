import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface HtmlSnippetBlockProps {
  html: string;
}

/**
 * Read-only display block for an HTML snippet attached to a finding's element
 * entry. Renders the raw HTML as escaped text inside a <pre> (NEVER as live
 * HTML — always treat snippets as untrusted strings, since the source is
 * scraped from the audited site). Includes a copy-to-clipboard button.
 */
export function HtmlSnippetBlock({ html }: HtmlSnippetBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(html);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (insecure context, no permission) — silently
      // ignore; the snippet is still selectable as text.
    }
  };

  return (
    <div className="relative group">
      <pre
        className="text-[11px] font-mono leading-relaxed text-text-secondary bg-surface-overlay border border-border-subtle rounded-md px-3 py-2 overflow-x-auto whitespace-pre-wrap break-all"
        style={{ fontFamily: 'var(--font-mono)' }}
      >
        {html}
      </pre>
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? 'Copied' : 'Copy HTML snippet'}
        className="absolute top-1.5 right-1.5 inline-flex items-center gap-1 text-[10px] font-semibold text-text-muted hover:text-text bg-surface-raised hover:bg-surface border border-border rounded px-1.5 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {copied ? <Check size={10} /> : <Copy size={10} />}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}
