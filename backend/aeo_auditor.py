import nltk
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List

def run_aeo_audit(soup: BeautifulSoup, html_content: str, sd_res: dict) -> Dict[str, Any]:
    checks = {}
    total_findings = 0
    positive_findings = []
    category_findings = []
    
    # Extract visible text using a simple heuristic
    # Remove script, style, nav, footer
    clean_soup = BeautifulSoup(html_content, 'lxml')
    for tag in clean_soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    text_content = clean_soup.get_text(separator=' ', strip=True)

    checks["readability"] = check_content_readability(text_content)
    checks["question_headings"] = check_question_headings(soup)
    checks["section_length"] = check_section_length(soup)
    checks["summary_section"] = check_summary_section(soup)
    checks["statistics_citations"] = check_statistics_citations(text_content)
    checks["author_publisher_schema"] = check_author_publisher_schema(sd_res)
    
    for check_key, check_val in checks.items():
        if check_val.get("status") == "pass":
            if "positive_message" in check_val:
                positive_findings.append({
                    "text": check_val["positive_message"],
                    "credibility_anchor": check_val.get("credibility_anchor")
                })
                del check_val["positive_message"]
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])
            
    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }

def create_finding(severity: str, description: str, recommendation: str, reference: str, anchor: str = None) -> Dict[str, str]:
    return {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference,
        "credibility_anchor": anchor
    }

def count_syllables(word: str) -> int:
    word = word.lower()
    count = 0
    vowels = "aeiouy"
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if count == 0:
        count += 1
    return count

def check_content_readability(text_content: str) -> Dict[str, Any]:
    findings = []
    anchor = "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations on average than Grade 11+ content (SE Ranking study of 2.3M pages, 2025)."
    
    try:
        sentences = nltk.sent_tokenize(text_content)
        words = nltk.word_tokenize(text_content)
    except Exception:
        # Fallback if nltk punkt fails
        sentences = text_content.split('.')
        words = text_content.split()

    # Filter out punctuation from words
    words = [w for w in words if w.isalpha()]

    total_sentences = len(sentences) if len(sentences) > 0 else 1
    total_words = len(words) if len(words) > 0 else 1
    total_syllables = sum(count_syllables(w) for w in words)

    grade = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    grade = round(grade, 1)

    status = "pass"
    if grade >= 11:
        findings.append(create_finding("high", f"Content readability is at Grade {grade}, significantly above the optimal range of 6-8.", "Simplify sentence structure and use shorter words.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"
    elif grade >= 9:
        findings.append(create_finding("medium", f"Content readability is at Grade {grade}, slightly above optimal range.", "Consider simplifying sentences to aim for Grade 6-8.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"

    res = {
        "status": status,
        "details": {"flesch_kincaid_grade": grade, "words": total_words, "sentences": total_sentences},
        "credibility_anchor": anchor
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = f"Content readability is optimal for AI citation (Grade {grade})."

    return res

def check_question_headings(soup: BeautifulSoup) -> Dict[str, Any]:
    findings = []
    anchor = "AI systems tend to surface content that uses Q&A-style formatting and structured summaries (Semrush AI Search Study, 2026). FAQ sections in content correlate with 4.9 citations vs 4.4 without (SE Ranking, 2025)."
    
    headings = soup.find_all(['h2', 'h3'])
    total_headings = len(headings)
    
    question_words = ["what", "why", "how", "when", "where", "which", "do", "does", "is", "are", "can", "should"]
    question_count = 0
    
    for h in headings:
        text = h.get_text(strip=True).lower()
        if any(text.startswith(w) for w in question_words) or "?" in text:
            question_count += 1
            
    pct = (question_count / total_headings * 100) if total_headings > 0 else 0
    
    status = "pass"
    if pct < 10 and total_headings > 0:
        findings.append(create_finding("medium", f"Very few question-based headings detected ({round(pct)}%).", "Convert more H2/H3 headings into question format for better AI discoverability.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"
    elif pct <= 20 and total_headings > 0:
        findings.append(create_finding("medium", f"Moderate number of question-based headings detected ({round(pct)}%).", "Consider converting more headings to questions.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"

    res = {
        "status": status,
        "details": {"total_h2_h3": total_headings, "question_headings": question_count, "percentage": round(pct, 1)},
        "credibility_anchor": anchor
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = "Good use of question-based headings for AI discoverability."
        
    return res

def check_section_length(soup: BeautifulSoup) -> Dict[str, Any]:
    findings = []
    anchor = "Content with 100-150 words per section earns the most AI citations, with a sweet spot for AI parsability (SE Ranking study of 2.3M pages, 2025)."
    
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    section_lengths = []
    
    for i in range(len(headings)):
        h = headings[i]
        next_h = headings[i+1] if i + 1 < len(headings) else None
        
        # Collect text between h and next_h
        text_nodes = []
        curr = h.next_sibling
        while curr and curr != next_h:
            # If it's a tag, we can get text
            if curr.name and curr.name not in ['script', 'style', 'nav', 'footer', 'aside']:
                if curr.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
                text_nodes.append(curr.get_text(separator=' ', strip=True))
            elif curr.string:
                text_nodes.append(str(curr.string).strip())
            curr = curr.next_sibling
            
        full_text = " ".join(text_nodes)
        try:
            words = nltk.word_tokenize(full_text)
        except Exception:
            words = full_text.split()
            
        words = [w for w in words if w.isalpha()]
        if len(words) > 0:
            section_lengths.append(len(words))
            
    avg_words = sum(section_lengths) / len(section_lengths) if section_lengths else 0
    
    status = "pass"
    if avg_words < 50 or avg_words > 300:
        findings.append(create_finding("high", f"Average section length is {round(avg_words)} words, significantly outside the optimal range.", "Break up long sections or expand very short ones to average 100-200 words.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"
    elif avg_words < 100 or avg_words > 200:
        findings.append(create_finding("medium", f"Average section length is {round(avg_words)} words, slightly outside the optimal range.", "Aim for 100-200 words per section.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"

    res = {
        "status": status,
        "details": {"average_words_per_section": round(avg_words, 1)},
        "credibility_anchor": anchor
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = f"Section lengths (avg {round(avg_words)} words) are in the optimal range for AI citation."
        
    return res

def check_summary_section(soup: BeautifulSoup) -> Dict[str, Any]:
    findings = []
    anchor = "Structured summaries and clearly organized copy are patterns that AI systems tend to surface more frequently (Semrush AI Search Study, 2026)."
    
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    summary_words = ["tl;dr", "tldr", "summary", "key takeaways", "in brief", "overview", "at a glance", "quick summary"]
    
    found = False
    for h in headings:
        text = h.get_text(strip=True).lower()
        if any(w in text for w in summary_words):
            found = True
            break
            
    if not found:
        findings.append(create_finding("medium", "No summary or TL;DR section detected.", "Add a clear summary or 'Key Takeaways' section.", "https://www.semrush.com/blog/technical-seo-impact-on-ai-search-study/", anchor))

    res = {
        "status": "pass" if found else "fail",
        "details": {"summary_found": found},
        "credibility_anchor": anchor
    }
    if found:
        res["positive_message"] = "Summary section detected. This helps AI systems extract key information."
    else:
        res["findings"] = findings
        
    return res

def check_statistics_citations(text_content: str) -> Dict[str, Any]:
    findings = []
    anchor = "Content containing citations, statistics, and quotations achieves 30-40% higher visibility in AI responses (Princeton GEO Research)."
    
    # regex matches
    pct_matches = re.findall(r'\d+%', text_content)
    mult_matches = re.findall(r'\d+(?:\.\d+)?x\b', text_content)
    dollar_matches = re.findall(r'\$[\d,]+', text_content)
    large_num_matches = re.findall(r'\b\d{1,3}(?:,\d{3})+\b', text_content)
    citation_matches = re.findall(r'\[\d+\]', text_content)
    year_matches = re.findall(r'\([^)]*?\b(?:19|20)\d{2}\b[^)]*?\)', text_content)
    
    total_stats = len(pct_matches) + len(mult_matches) + len(dollar_matches) + len(large_num_matches) + len(citation_matches) + len(year_matches)
    
    status = "pass"
    if total_stats <= 2:
        findings.append(create_finding("high", f"Very few statistics or citations found ({total_stats}).", "Include more data points, statistics, and verifiable citations in your content.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"
    elif total_stats <= 4:
        findings.append(create_finding("medium", f"Moderate number of statistics or citations found ({total_stats}).", "Consider adding more statistics and citations.", "https://www.superlines.io/articles/ai-search-statistics/", anchor))
        status = "fail"

    res = {
        "status": status,
        "details": {"data_points_found": total_stats},
        "credibility_anchor": anchor
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = f"Good use of statistics and data points ({total_stats} found)."
        
    return res

def check_author_publisher_schema(sd_res: dict) -> Dict[str, Any]:
    findings = []
    anchor = "Websites with author schema are 3x more likely to appear in AI answers (BrightEdge, 2026)."
    
    # Extract json-ld from sd_res checks
    # To do this correctly, we might need the raw JSON-LD data. But we can also just check if the SD auditor found Author and Publisher.
    # However, since AEO auditor receives sd_res (the dict returned by structured_data_auditor), let's inspect the `findings` to see if there are any related to Article/BlogPosting missing author/publisher.
    # But a cleaner way is to parse the original JSON-LD.
    # Since we don't have raw JSON-LD passed in, I'll update main.py to pass json_ld_data or just look inside sd_res if we can infer it. 
    # Actually, a better way is to see if any positive finding or anything in sd_res mentions it. Or I can add raw json_ld to `sd_res["raw_json_ld"]` in structured_data_auditor.py. Let me assume `sd_res` contains "raw_json_ld".
    
    json_ld_data = sd_res.get("raw_json_ld", [])
    
    has_article = False
    has_author = False
    has_publisher = False
    
    def walk(entity):
        nonlocal has_article, has_author, has_publisher
        if not isinstance(entity, dict): return
        t = entity.get("@type", "")
        if isinstance(t, list): t = t[0]
        
        if t in ["Article", "BlogPosting", "NewsArticle"]:
            has_article = True
            author = entity.get("author")
            if author:
                if isinstance(author, dict) and author.get("@type") in ["Person", "Organization"]:
                    has_author = True
                elif isinstance(author, list) and any(isinstance(a, dict) and a.get("@type") in ["Person", "Organization"] for a in author):
                    has_author = True
            
            publisher = entity.get("publisher")
            if publisher:
                if isinstance(publisher, dict) and publisher.get("@type") in ["Organization", "Person"]:
                    has_publisher = True
                elif isinstance(publisher, list) and any(isinstance(p, dict) and p.get("@type") in ["Organization", "Person"] for p in publisher):
                    has_publisher = True
                    
        for v in entity.values():
            if isinstance(v, dict): walk(v)
            elif isinstance(v, list):
                for item in v: walk(item)

    for item in json_ld_data:
        walk(item)
        
    status = "pass"
    if has_article:
        if not has_author:
            findings.append(create_finding("high", "Author schema missing from Article/BlogPosting.", "Add an author property of type Person.", "schema.org", anchor))
            status = "fail"
        if not has_publisher:
            findings.append(create_finding("medium", "Publisher schema missing from Article/BlogPosting.", "Add a publisher property of type Organization.", "schema.org", anchor))
            status = "fail"
    else:
        # Check if the page seems like an article? The spec says:
        # "No Article schema => medium => No Article or BlogPosting schema found to evaluate."
        findings.append(create_finding("medium", "No Article or BlogPosting schema found to evaluate author attribution.", "If this is content, implement Article schema.", "schema.org", anchor))
        status = "fail"

    res = {
        "status": status,
        "details": {"has_article": has_article, "has_author": has_author, "has_publisher": has_publisher},
        "credibility_anchor": anchor
    }
    
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = "Author and publisher schema correctly implemented within Article."
        
    return res
