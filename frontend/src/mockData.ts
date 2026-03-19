export const mockReport = {
  url: "https://example-webflow.com",
  audit_timestamp: new Date().toISOString(),
  overall_score: 62,
  overall_label: "Needs Improvement",
  categories: {
    semantic_html: {
      score: 71,
      label: "Good",
      checks: {
        document_foundation: {
          findings: [
            {
              severity: "medium",
              description: "Missing lang attribute on <html> element.",
              recommendation: "Add lang='en' (or appropriate language code) to the <html> tag for proper screen reader pronunciation.",
              reference: "https://www.w3.org/WAI/WCAG21/Understanding/language-of-page.html"
            }
          ]
        },
        heading_hierarchy: {
          findings: [
            {
              severity: "high",
              description: "Heading hierarchy skips from H1 to H3 — missing H2 level.",
              recommendation: "Restructure headings to follow sequential order (H1 → H2 → H3). In Webflow, adjust heading elements in the Navigator panel.",
              reference: "https://www.w3.org/WAI/tutorials/page-structure/headings/"
            }
          ]
        },
        landmark_elements: {
          findings: []
        },
        alt_text_coverage: {
          findings: [
            {
              severity: "critical",
              description: "12 of 18 images are missing alt text attributes.",
              recommendation: "Add descriptive alt text to all informational images. Use empty alt='' only for decorative images. In Webflow, use the Image Settings panel.",
              reference: "https://www.w3.org/WAI/tutorials/images/"
            }
          ]
        }
      }
    },
    structured_data: {
      score: 45,
      label: "Poor",
      checks: {
        jsonld_presence: {
          findings: [
            {
              severity: "critical",
              description: "No JSON-LD structured data found on the page.",
              recommendation: "Add at minimum an Organization schema via JSON-LD in the page <head>. Use Google's Structured Data Markup Helper to generate the code.",
              reference: "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data"
            }
          ]
        },
        microdata_presence: {
          findings: [
            {
              severity: "medium",
              description: "No microdata (itemscope/itemprop) found on the page.",
              recommendation: "Consider adding microdata to key content elements like reviews, products, or FAQ sections for enhanced search appearance.",
              reference: "https://schema.org/docs/gs.html"
            }
          ]
        }
      }
    },
    css_quality: {
      score: 78,
      label: "Good",
      checks: {
        framework_detection: {
          findings: []
        },
        naming_consistency: {
          findings: [
            {
              severity: "medium",
              description: "Mixed naming conventions detected: 62% Client-First, 38% custom naming.",
              recommendation: "Standardize CSS class naming to follow Client-First conventions consistently. Refactor custom classes to match the detected framework pattern.",
              reference: "https://finsweet.com/client-first"
            }
          ]
        },
        inline_styles: {
          findings: [
            {
              severity: "medium",
              description: "Found 14 inline style attributes across the page.",
              recommendation: "Move inline styles to Webflow classes. Inline styles reduce maintainability and increase specificity conflicts.",
              reference: "https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Cascade_and_inheritance"
            }
          ]
        }
      }
    },
    js_bloat: {
      score: 85,
      label: "Good",
      checks: {
        webflow_js_bloat: {
          findings: [
            {
              severity: "medium",
              description: "Webflow Interactions 2.0 (IX2) engine loaded (+43kB) but only 2 simple interactions detected.",
              recommendation: "Consider replacing simple opacity/transform animations with CSS transitions to eliminate the IX2 dependency.",
              reference: "https://university.webflow.com/lesson/intro-to-interactions"
            }
          ]
        },
        third_party_scripts: {
          findings: []
        }
      }
    },
    accessibility: {
      score: 48,
      label: "Poor",
      checks: {
        axe_core_scan: {
          findings: [
            {
              severity: "critical",
              description: "Color contrast ratio of 2.8:1 found on 6 text elements (minimum required: 4.5:1 for normal text).",
              recommendation: "Increase contrast ratio to at least 4.5:1 for normal text and 3:1 for large text. Use WebAIM Contrast Checker to verify.",
              reference: "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html"
            },
            {
              severity: "high",
              description: "3 form inputs missing associated <label> elements.",
              recommendation: "Add visible <label> elements linked via for/id attributes, or use aria-label for visually hidden labels.",
              reference: "https://www.w3.org/WAI/tutorials/forms/labels/"
            }
          ]
        },
        touch_target_size: {
          findings: [
            {
              severity: "high",
              description: "8 interactive elements have touch targets smaller than 44x44px (WCAG 2.5.5).",
              recommendation: "Ensure all clickable elements have a minimum touch target of 44x44 CSS pixels. Add padding if needed.",
              reference: "https://www.w3.org/WAI/WCAG21/Understanding/target-size.html"
            }
          ]
        },
        focus_styles: {
          findings: [
            {
              severity: "high",
              description: "No visible focus indicators found on interactive elements.",
              recommendation: "Add :focus-visible styles with a visible outline (minimum 2px) to all interactive elements. Webflow's default focus styles are often insufficient.",
              reference: "https://www.w3.org/WAI/WCAG21/Understanding/focus-visible.html"
            }
          ]
        }
      }
    }
  },
  positive_findings: [
    "Valid HTML5 doctype declaration found.",
    "Single H1 element present — correct document outline.",
    "All landmark regions (header, main, footer) are properly implemented.",
    "Client-First CSS framework detected — good foundation for maintainability.",
    "No render-blocking scripts found in <head>.",
    "External stylesheet count is within acceptable range (2 files).",
    "No third-party script bloat detected."
  ],
  summary: {
    total_findings: 13,
    critical: 3,
    high: 4,
    medium: 6,
    top_priorities: [
      "Add descriptive alt text to all 12 images missing alt attributes.",
      "Implement JSON-LD structured data (minimum: Organization schema).",
      "Fix color contrast issues on 6 text elements to meet WCAG 4.5:1 ratio.",
      "Add visible focus indicators to all interactive elements.",
      "Ensure all touch targets meet the 44x44px minimum size."
    ]
  }
};
