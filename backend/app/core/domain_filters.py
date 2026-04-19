"""Domain filtering configuration for wine photo search.

Trusted domains improve search precision by focusing on wine-specific sources
and filtering out stock photo sites and marketplaces with low-quality images.
"""

# High-trust wine merchant and auction sites
TRUSTED_WINE_DOMAINS = frozenset([
    # Major wine retailers
    "wine.com",
    "totalwine.com",
    "millesima.com",
    "xtrawine.com",
    "tannico.it",
    "vino.com",
    "klwines.com",
    "cruworldwine.com",
    "thewinesociety.com",
    "chambersstwines.com",
    "thesortingtable.com",
    "bbr.com",
    "hedonism.co.uk",
    "b-21.com",
    "saratogawine.com",
    "winehouse.com",
    "wineexpress.com",
    "garyswine.com",
    "melandrose.com",
    "vinfolio.com",
    "jjbuckley.com",
    "wallywine.com",
    "mcduffswine.com",
    "therarewinestore.com",
    "nickollsandperks.co.uk",
    "wilsonandmorgan.com",
    "rarewineco.com",
    "enotecaproperzio.com",
    "bernabei.it",
    "callmewine.com",
    "winemerchant.com",
    "cinderella.com",
    "winelibrary.com",
    
    # Wine auction houses (high-quality images)
    "vintagegrandcru.com",
    "benchmarkwinegroup.com",
    "winebid.com",
    "idealwine.com",
    "ackerwines.com",
    "sothebys.com",
    "christies.com",
    "spectrumwine.com",
    "wineauctioneer.com",
    "zachys.com",
    "bidforwine.co.uk",
    "wineconsigners.com",
    
    # Wine databases and communities (excellent label photos)
    "wine-searcher.com",
    "vivino.com",
    "cellartracker.com",
    
    # Wine media (professional photography)
    "decanter.com",
    "wineenthusiast.com",
    "jamessuckling.com",
    "robertparker.com",
    "jancisrobinson.com",
    "winemag.com",
])

# Domains to explicitly exclude (stock photos, marketplaces, AI-generated)
EXCLUDED_DOMAINS = frozenset([
    # Stock photo sites
    "shutterstock.com",
    "gettyimages.com",
    "alamy.com",
    "123rf.com",
    "istockphoto.com",
    "dreamstime.com",
    "depositphotos.com",
    "canstockphoto.com",
    "bigstockphoto.com",
    "fotolia.com",
    
    # Social media (variable quality, often not bottle-focused)
    "pinterest.com",
    "flickr.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    
    # General marketplaces (often lifestyle shots, not clean bottle photos)
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "walmart.com",
    "target.com",
    "costco.com",
    
    # AI image generators
    "craiyon.com",
    "midjourney.com",
    "stablediffusionweb.com",
    
    # Other problematic sites
    "skuvantage.com.au",
])

# Domain suffixes to match (for subdomain handling)
TRUSTED_DOMAIN_SUFFIXES = tuple(sorted(TRUSTED_WINE_DOMAINS, key=len, reverse=True))
EXCLUDED_DOMAIN_SUFFIXES = tuple(sorted(EXCLUDED_DOMAINS, key=len, reverse=True))


def is_trusted_domain(domain: str) -> bool:
    """Check if domain is in the trusted wine sites list.
    
    Handles subdomains (e.g., shop.wine.com matches wine.com).
    
    Args:
        domain: The domain to check (e.g., "www.wine.com" or "wine.com")
        
    Returns:
        True if domain or its parent is in TRUSTED_WINE_DOMAINS
    """
    domain_lower = domain.lower().strip()
    
    # Direct match
    if domain_lower in TRUSTED_WINE_DOMAINS:
        return True
    
    # Check if domain ends with any trusted suffix
    # This handles subdomains like "shop.wine.com" -> matches "wine.com"
    for suffix in TRUSTED_DOMAIN_SUFFIXES:
        if domain_lower == suffix or domain_lower.endswith("." + suffix):
            return True
    
    return False


def is_excluded_domain(domain: str) -> bool:
    """Check if domain should be excluded from results.
    
    Args:
        domain: The domain to check
        
    Returns:
        True if domain should be excluded
    """
    domain_lower = domain.lower().strip()
    
    # Direct match
    if domain_lower in EXCLUDED_DOMAINS:
        return True
    
    # Check suffixes for subdomain matching
    for suffix in EXCLUDED_DOMAIN_SUFFIXES:
        if domain_lower == suffix or domain_lower.endswith("." + suffix):
            return True
    
    return False


def get_domain_trust_score(domain: str) -> float:
    """Get trust score for a domain.
    
    Returns:
        0.90 for trusted wine sites
        0.75 for neutral sites
        0.00 for excluded sites (should be filtered out)
    """
    if is_excluded_domain(domain):
        return 0.0
    
    if is_trusted_domain(domain):
        return 0.90
    
    return 0.75  # Neutral - neither explicitly trusted nor excluded


def filter_candidates_by_domain(candidates: list) -> list:
    """Filter candidate list to remove excluded domains.
    
    Args:
        candidates: List of Candidate objects
        
    Returns:
        Filtered list with excluded domains removed
    """
    return [c for c in candidates if not is_excluded_domain(c.source_domain)]


def sort_candidates_by_domain_trust(candidates: list) -> list:
    """Sort candidates by domain trust score (highest first).
    
    Args:
        candidates: List of Candidate objects
        
    Returns:
        Sorted list with trusted domains first
    """
    return sorted(
        candidates,
        key=lambda c: get_domain_trust_score(c.source_domain),
        reverse=True
    )


def build_site_restricted_queries(wine_name: str, vintage: str, max_sites: int = 3) -> list[str]:
    """Build search queries with site restrictions for top trusted domains.
    
    Args:
        wine_name: The wine name to search
        vintage: The vintage year
        max_sites: Maximum number of site-restricted queries to generate
        
    Returns:
        List of site-restricted search queries
    """
    # Prioritize sites known for good bottle photography
    priority_sites = [
        "wine-searcher.com",
        "vivino.com",
        "cellartracker.com",
        "wine.com",
        "klwines.com",
        "jjbuckley.com",
        "sothebys.com",
        "christies.com",
    ]
    
    queries = []
    base_query = f'"{wine_name}" {vintage} bottle'
    
    for site in priority_sites[:max_sites]:
        queries.append(f"{base_query} site:{site}")
    
    return queries
