"""Compact constructors for seed rows. Dates are 'MM-DD' strings; rows are plain dicts."""

# country -> (ISO-3166 alpha-2, continent)
COUNTRIES = {
    "USA": ("US", "North America"), "Canada": ("CA", "North America"), "Mexico": ("MX", "North America"),
    "UK": ("GB", "Europe"), "Germany": ("DE", "Europe"), "France": ("FR", "Europe"), "Italy": ("IT", "Europe"),
    "Spain": ("ES", "Europe"), "Austria": ("AT", "Europe"), "Switzerland": ("CH", "Europe"),
    "Netherlands": ("NL", "Europe"), "Denmark": ("DK", "Europe"), "Portugal": ("PT", "Europe"),
    "Czechia": ("CZ", "Europe"), "Finland": ("FI", "Europe"), "Norway": ("NO", "Europe"), "Greece": ("GR", "Europe"), "Ireland": ("IE", "Europe"),
    "China": ("CN", "Asia"), "Japan": ("JP", "Asia"), "South Korea": ("KR", "Asia"), "Singapore": ("SG", "Asia"),
    "India": ("IN", "Asia"), "UAE": ("AE", "Asia"), "Thailand": ("TH", "Asia"), "Taiwan": ("TW", "Asia"),
    "Australia": ("AU", "Oceania"), "New Zealand": ("NZ", "Oceania"), "Brazil": ("BR", "South America"),
    "Rwanda": ("RW", "Africa"), "South Africa": ("ZA", "Africa"), "Morocco": ("MA", "Africa"),
    "Online": ("", "Online"),
}


def flag(country):
    iso = COUNTRIES[country][0]
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in iso) if iso else "🌐"


# default template / portal helpers ------------------------------------------------
STYLE_URLS = {
    "ACM sigconf": "https://www.acm.org/publications/proceedings-template",
    "IEEEtran": "https://www.ieee.org/conferences/publishing/templates.html",
    "Springer LNCS": "https://www.springer.com/gp/computer-science/lncs/conference-proceedings-guidelines",
    "NeurIPS": "https://neurips.cc/Conferences/2025/PaperInformation/StyleFiles",
    "ICML": "https://icml.cc/Conferences/2025/AuthorInstructions",
    "ICLR": "https://github.com/ICLR/Master-Template",
    "CVPR": "https://github.com/cvpr-org/author-kit",
    "ACL": "https://github.com/acl-org/acl-style-files",
    "AAAI": "https://aaai.org/authorkit/",
    "IJCAI": "https://www.ijcai.org/authors_kit",
    "PMLR": "https://proceedings.mlr.press/spec.html",
    "USENIX": "https://www.usenix.org/conferences/author-resources/paper-templates",
    "Elsevier": "https://www.elsevier.com/authors/policies-and-guidelines/latex-instructions",
    "Nature": "https://www.nature.com/nature/for-authors/formatting-guide",
    "Science": "https://www.science.org/content/page/science-instructions-authors",
    "PNAS": "https://www.pnas.org/author-center/submitting-your-manuscript",
    "Oxford Academic": "https://academic.oup.com/bioinformatics/pages/instructions_for_authors",
    "Springer Nature": "https://www.springernature.com/gp/authors/campaigns/latex-author-support",
    "JMLR": "https://www.jmlr.org/format/format.html",
    "Wiley": "https://authorservices.wiley.com/author-resources/Journal-Authors/Prepare/new-submission.html",
    "Lancet": "https://www.thelancet.com/digital-health/information-for-authors",
}


def _row(**kw):
    c = kw["country"]
    kw.setdefault("flag", flag(c))
    kw.setdefault("continent", COUNTRIES[c][1])
    kw.setdefault("template_url", STYLE_URLS.get(kw.get("style", ""), ""))
    kw.setdefault("portal", kw.get("url", ""))
    return kw


def conf(acr, name, domain, tags, pub, core, ccf, h5, h5m, acc, dates, city, country, pages, style, review,
         url, desc, *, kind="Conference", mode="In-Person", oa=True, apc=0, tz="AoE", portal="", scope="",
         days=5, open_days=90):
    """dates = (abstract, submission, notification, camera_ready, event_start) as 'MM-DD' (abstract may be None)."""
    a, s, n, c, e = dates
    return _row(
        acr=acr, name=name, type=kind, domain=domain, tags=tags, pub=pub, core=core, ccf=ccf, h5=h5, h5m=h5m,
        acc=acc, abs=a, sub=s, notif=n, cam=c, ev=e, days=days, city=city, country=country, pages=pages,
        style=style, review=review, url=url, desc=desc, mode=mode, oa=oa, apc=apc, tz=tz,
        portal=portal or url, scope=scope, rolling=False, open_days=open_days,
        IF=None, quartile="", citescore=None, sjr=None, issn="",
    )


def jrnl(acr, name, domain, tags, pub, IF, quartile, citescore, sjr, issn, acc, oa, apc, pages, style, review,
         url, desc, *, portal="", scope=""):
    return _row(
        acr=acr, name=name, type="Journal", domain=domain, tags=tags, pub=pub, core="Unranked", ccf="Unranked",
        h5=None, h5m=None, acc=acc, abs=None, sub=None, notif=None, cam=None, ev=None, days=0,
        city="", country="Online", pages=pages, style=style, review=review, url=url, desc=desc,
        mode="Virtual", oa=oa, apc=apc, tz="UTC", portal=portal or url, scope=scope, rolling=True,
        open_days=0, IF=IF, quartile=quartile, citescore=citescore, sjr=sjr, issn=issn,
    )
