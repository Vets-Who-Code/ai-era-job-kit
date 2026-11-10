"""jobdata: keyless, standard-library-only market data helpers for the
"Getting the Job in the Era of AI" course kit.

Sources (all public, no API key):
  * O*NET database text files (onetcenter.org) - occupations, Technology
    Skills with Hot Technology / In Demand flags, Skills importance.
  * BLS Employment Projections table (bls.gov/emp) - 10-year growth,
    annual openings, median wage.
  * BLS Public Data API v1 (api.bls.gov) - OEWS wages, no registration.
  * Job postings - your own saved postings, or public Greenhouse / Lever /
    Ashby job boards for companies you name.

Rule of the kit: numbers come from a live pull on every run. If a pull
fails, the tools stop and say so. They never fall back to remembered or
made-up figures.
"""

__version__ = "1.0.0"
