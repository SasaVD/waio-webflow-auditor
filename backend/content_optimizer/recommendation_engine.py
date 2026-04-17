"""Generate increase/add/reduce/remove recommendations from WDF*IDF analysis."""
from .schema import TermAnalysis, TermClassification, Recommendation, RecommendationType


def generate_recommendations(terms: list[TermAnalysis]) -> list[Recommendation]:
    """Generate 4 types of recommendations:
    - INCREASE: term exists but below competitor average
    - ADD: term missing from target but used by 3+ competitors
    - REDUCE: term significantly above competitor max (over-optimization)
    - REMOVE: AI filler terms that should be replaced
    """
    recommendations: list[Recommendation] = []

    for term in terms:
        # REMOVE: AI filler
        if term.classification == TermClassification.FILLER:
            if term.target_frequency > 0:
                recommendations.append(Recommendation(
                    type=RecommendationType.REMOVE,
                    term=term.term,
                    classification=term.classification,
                    reason=(
                        f"AI-generic {term.filler_category or 'phrase'} with no SEO value. "
                        f"Used {term.target_frequency}x on your page. "
                        f"Replace with specific, concrete language."
                    ),
                    target_frequency=term.target_frequency,
                    suggested_frequency=0,
                    priority=_priority_score(term, RecommendationType.REMOVE),
                ))
            continue

        # ADD: missing from target, competitors use it
        if term.target_frequency == 0 and term.docs_containing >= 3:
            if term.classification in (TermClassification.CORE, TermClassification.SEMANTIC):
                avg_freq = term.competitor_avg_frequency
                recommendations.append(Recommendation(
                    type=RecommendationType.ADD,
                    term=term.term,
                    classification=term.classification,
                    reason=(
                        f"Missing from your page but used by "
                        f"{term.docs_containing - 1} competitors "
                        f"(avg {avg_freq:.0f}x). "
                        + (
                            "Critical gap \u2014 directly related to target keyword."
                            if term.classification == TermClassification.CORE
                            else "Semantically important term competitors use."
                        )
                    ),
                    target_frequency=0,
                    suggested_frequency=max(1, round(avg_freq)),
                    priority=_priority_score(term, RecommendationType.ADD),
                ))
            continue

        # REDUCE: target significantly exceeds competitor maximum
        if term.target_wdf_idf > 0 and term.competitor_max_wdf_idf > 0:
            if term.target_wdf_idf > term.competitor_max_wdf_idf * 1.5:
                recommendations.append(Recommendation(
                    type=RecommendationType.REDUCE,
                    term=term.term,
                    classification=term.classification,
                    reason=(
                        f"Used {term.target_frequency}x on your page \u2014 "
                        f"{term.target_wdf_idf / term.competitor_avg_wdf_idf:.1f}x "
                        f"the competitor average. Reduce to avoid over-optimization."
                    ),
                    target_frequency=term.target_frequency,
                    suggested_frequency=max(1, round(term.competitor_avg_frequency)),
                    priority=_priority_score(term, RecommendationType.REDUCE),
                ))
                continue

        # INCREASE: target below competitor average
        if term.target_wdf_idf > 0 and term.competitor_avg_wdf_idf > 0:
            ratio = term.target_wdf_idf / term.competitor_avg_wdf_idf
            if ratio < 0.5:
                recommendations.append(Recommendation(
                    type=RecommendationType.INCREASE,
                    term=term.term,
                    classification=term.classification,
                    reason=(
                        f"Used {term.target_frequency}x on your page vs competitor "
                        f"average of {term.competitor_avg_frequency:.0f}x. "
                        f"Increase to reach optimal range."
                    ),
                    target_frequency=term.target_frequency,
                    suggested_frequency=max(
                        term.target_frequency + 1,
                        round(term.competitor_avg_frequency),
                    ),
                    priority=_priority_score(term, RecommendationType.INCREASE),
                ))

    recommendations.sort(key=lambda r: r.priority, reverse=True)
    return recommendations


def _priority_score(term: TermAnalysis, rec_type: RecommendationType) -> float:
    """Higher = more impactful to fix."""
    base = term.competitor_avg_wdf_idf * 100

    multiplier = {
        TermClassification.CORE: 3.0,
        TermClassification.SEMANTIC: 2.0,
        TermClassification.AUXILIARY: 1.0,
        TermClassification.FILLER: 1.5,
    }.get(term.classification, 1.0)

    type_boost = {
        RecommendationType.ADD: 1.5,
        RecommendationType.REMOVE: 1.3,
        RecommendationType.INCREASE: 1.0,
        RecommendationType.REDUCE: 0.8,
    }.get(rec_type, 1.0)

    return base * multiplier * type_boost
