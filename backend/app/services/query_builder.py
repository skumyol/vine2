from backend.app.core.domain_filters import build_site_restricted_queries
from backend.app.models.sku import AnalyzeRequest, ParsedIdentity


def build_queries(payload: AnalyzeRequest, parsed: ParsedIdentity) -> list[str]:
    wine_name = " ".join(payload.wine_name.split())
    vintage = payload.vintage.strip()
    queries: list[str] = []
    exact = f'"{wine_name}" {vintage} bottle'
    queries.append(exact)
    queries.append(f"{wine_name} {vintage}")
    queries.append(f"{parsed.normalized_wine_name} {vintage} bottle")
    queries.append(f'"{wine_name}" {vintage} label')
    queries.append(f'"{wine_name}" {vintage} wine')

    if parsed.producer:
        queries.append(f"{parsed.producer} {vintage} wine bottle")
        if parsed.appellation:
            queries.append(f'{parsed.producer} "{parsed.appellation}" {vintage} bottle')

    if parsed.vineyard_or_cuvee:
        queries.append(f'{parsed.producer or wine_name} "{parsed.vineyard_or_cuvee}" {vintage}')
        queries.append(f'"{parsed.vineyard_or_cuvee}" {vintage} wine bottle')

    queries.extend(build_site_restricted_queries(wine_name, vintage))

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = " ".join(query.split())
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped
