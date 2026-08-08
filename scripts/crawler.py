"""Etape 1 du pipeline : collecte par crawl. Ecrit dans seo/donnees/crawl/.

Ce que produit ce script est le seul socle `[T1 observe]` de l'etude : 29 des
87 noeuds citent le crawl dans leur methode, et les 53 noeuds marques `SD` supposent
tous qu'on peut lire le site. Sans lui, chaque audit recommence la collecte a la main
et deux audits du meme site ne sont pas comparables.

Garde-fous, tenus par construction :
  - `robots.txt` respecte, sans exception ni option pour le contourner ;
  - plafond de pages declare et applique ;
  - delai entre requetes, pour ne pas peser sur le site audite ;
  - meme hote uniquement, jamais de sortie de domaine ;
  - PAS de rendu JavaScript : ce qui est injecte cote client est invisible. Le
    resultat le declare, et les noeuds concernes basculent en non mesurable plutot
    que de conclure a l'absence d'un contenu qui existe peut-etre.

Usage :
    python scripts/crawler.py --projet . --url https://exemple.fr
    python scripts/crawler.py --projet . --url https://exemple.fr --max 500 --delai 0.3

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import deque
from html.parser import HTMLParser
from pathlib import Path

AGENT = "forge-seo/1.0 (audit SEO ; +contact via le commanditaire de l'audit)"
PLAFOND = 200
DELAI = 0.5
TIMEOUT = 15

# Heuristique de gabarit : l'URL dit souvent le type de page. Approximative et
# declaree comme telle -- elle sert a stratifier l'echantillon, pas a conclure.
GABARITS = [
    (r"^/?$", "accueil"),
    (r"/(blog|actualite|article|news)/", "article"),
    (r"/(categorie|category|rubrique)/", "categorie"),
    (r"/(produit|product|gite|chambre|offre)/", "produit"),
    (r"/(contact|mentions|cgv|politique|legal)", "service"),
    (r"/(panier|checkout|commande|reservation)", "transactionnel"),
]


class Page(HTMLParser):
    """Extrait ce dont la grille a besoin, sans dependance."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = None
        self.h1 = None
        self.canonical = None
        self.robots = ""
        self.liens: list[tuple[str, bool]] = []   # (href, contextuel)
        self.mots = 0
        self._dans = None
        self._nav = 0          # profondeur dans nav/header/footer/aside
        self._script = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "header", "footer", "aside"):
            self._nav += 1
        elif tag in ("script", "style"):
            self._script += 1
        elif tag == "title" and self.title is None:
            self._dans = "title"
        elif tag == "h1" and self.h1 is None:
            self._dans = "h1"
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href")
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.robots = (a.get("content") or "").lower()
        elif tag == "a" and a.get("href"):
            self.liens.append((a["href"], self._nav == 0))

    def handle_endtag(self, tag):
        if tag in ("nav", "header", "footer", "aside"):
            self._nav = max(0, self._nav - 1)
        elif tag in ("script", "style"):
            self._script = max(0, self._script - 1)
        elif tag in ("title", "h1"):
            self._dans = None

    def handle_data(self, data):
        if self._dans == "title":
            self.title = (self.title or "") + data
        elif self._dans == "h1":
            self.h1 = (self.h1 or "") + data
        elif self._script == 0:
            self.mots += len(data.split())


def normaliser(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    chemin = p.path or "/"
    if len(chemin) > 1 and chemin.endswith("/"):
        chemin = chemin[:-1]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, chemin, p.query, ""))


def gabarit(chemin: str) -> str:
    for motif, nom in GABARITS:
        if re.search(motif, chemin):
            return nom
    return "page"


def recuperer(url: str) -> tuple[int, str, bytes, list[str]]:
    """Retourne (code, url_finale, corps, chaine_de_redirection)."""
    chaine: list[str] = []

    class Suivi(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            chaine.append(f"{code} → {newurl}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    ouvreur = urllib.request.build_opener(Suivi)
    req = urllib.request.Request(url, headers={
        "User-Agent": AGENT, "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
    })
    try:
        with ouvreur.open(req, timeout=TIMEOUT) as r:
            brut = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                brut = gzip.decompress(brut)
            if "html" not in (r.headers.get("Content-Type") or ""):
                return r.status, r.url, b"", chaine
            return r.status, r.url, brut, chaine
    except urllib.error.HTTPError as e:
        return e.code, url, b"", chaine
    except Exception as e:  # reseau, DNS, TLS, timeout
        return 0, url, str(e).encode(), chaine


def crawler(racine: str, plafond: int, delai: float) -> dict:
    depart = normaliser(racine)
    hote = urllib.parse.urlsplit(depart).netloc

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(depart, "/robots.txt"))
    try:
        rp.read()
        robots_lu = True
    except Exception:
        robots_lu = False

    vues: dict[str, dict] = {}
    entrants: dict[str, int] = {}     # liens contextuels : flux d'autorite
    entrants_tous: dict[str, int] = {}  # tous liens : detection d'orphelines
    file = deque([(depart, 0)])
    connus = {depart}
    bloquees = 0

    while file and len(vues) < plafond:
        url, prof = file.popleft()
        if robots_lu and not rp.can_fetch(AGENT, url):
            bloquees += 1
            continue

        code, finale, corps, chaine = recuperer(url)
        time.sleep(delai)

        p = Page()
        if corps:
            try:
                p.feed(corps.decode("utf-8", "replace"))
            except Exception:
                pass

        chemin = urllib.parse.urlsplit(url).path or "/"
        indexable = None
        if code == 200:
            indexable = "noindex" not in p.robots
            if p.canonical:
                if normaliser(urllib.parse.urljoin(url, p.canonical)) != normaliser(url):
                    indexable = False

        vues[url] = {
            "url": chemin,
            "type_gabarit": gabarit(chemin),
            "profondeur_clic": prof,
            "code_http": code,
            "title": (p.title or "").strip() or None,
            "h1": (p.h1 or "").strip() or None,
            "canonical": (urllib.parse.urlsplit(
                urllib.parse.urljoin(url, p.canonical)).path if p.canonical else None),
            "indexable": indexable,
            "liens_internes_entrants": 0,
            "poids_ko": round(len(corps) / 1024, 1) if corps else 0.0,
            "preuve": "T1",
            "_mots": p.mots,
            "_redirections": chaine,
        }

        for href, contextuel in p.liens:
            cible = normaliser(urllib.parse.urljoin(url, href))
            if urllib.parse.urlsplit(cible).netloc != hote:
                continue
            entrants_tous[cible] = entrants_tous.get(cible, 0) + 1
            if contextuel:
                entrants[cible] = entrants.get(cible, 0) + 1
            if cible not in connus and len(connus) < plafond * 3:
                connus.add(cible)
                file.append((cible, prof + 1))

    for url, v in vues.items():
        # Le champ du schema mesure le flux d'autorite : liens contextuels seuls,
        # navigation et pied de page exclus.
        v["liens_internes_entrants"] = entrants.get(url, 0)
        v["_entrants_tous"] = entrants_tous.get(url, 0)

    pages = sorted(vues.values(), key=lambda x: (x["profondeur_clic"], x["url"]))
    # Orpheline = AUCUN lien entrant, navigation comprise. Une page liee seulement
    # depuis le menu n'est pas orpheline : elle est mal irriguee, ce que mesure deja
    # liens_internes_entrants.
    orphelines = [p["url"] for p in pages if p["_entrants_tous"] == 0
                  and p["profondeur_clic"] > 0]
    titres: dict[str, int] = {}
    for p in pages:
        if p["title"]:
            titres[p["title"]] = titres.get(p["title"], 0) + 1

    return {
        "collecte": {
            "outil": "forge-seo/crawler.py",
            "date": dt.date.today().isoformat(),
            "racine": depart,
            "plafond": plafond,
            "delai_s": delai,
            "robots_txt_lu": robots_lu,
            "urls_bloquees_par_robots": bloquees,
            "rendu_javascript": False,
            "limite": ("Sans rendu JavaScript : le contenu injecté côté client est "
                       "invisible. Ne pas conclure à l'absence d'un contenu qui "
                       "pourrait ne pas être dans le HTML initial."),
        },
        "synthese": {
            "pages_crawlees": len(pages),
            "urls_decouvertes": len(connus),
            "profondeur_max": max((p["profondeur_clic"] for p in pages), default=0),
            "erreurs_4xx_5xx": sum(1 for p in pages if p["code_http"] >= 400),
            "non_indexables": sum(1 for p in pages if p["indexable"] is False),
            "pages_orphelines": len(orphelines),
            "pages_sans_lien_contextuel": sum(
                1 for p in pages if p["liens_internes_entrants"] == 0),
            "titles_dupliques": sum(n for n in titres.values() if n > 1) -
                                sum(1 for n in titres.values() if n > 1),
            "pages_fines_sous_300_mots": sum(1 for p in pages if 0 < p["_mots"] < 300),
        },
        "pages": pages,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Crawl du site audité — étape 1 du pipeline.")
    p.add_argument("--projet", required=True, help="chemin du projet audité")
    p.add_argument("--url", required=True, help="URL racine du site")
    p.add_argument("--max", type=int, default=PLAFOND, help=f"plafond de pages ({PLAFOND})")
    p.add_argument("--delai", type=float, default=DELAI, help=f"délai entre requêtes ({DELAI}s)")
    args = p.parse_args()

    dossier = Path(args.projet).resolve() / "seo" / "donnees" / "crawl"
    if not dossier.parent.parent.is_dir():
        print(f"{dossier.parent.parent} absent — créer l'étude avec new_mission.py")
        return 1
    dossier.mkdir(parents=True, exist_ok=True)

    print(f"crawl de {args.url} — plafond {args.max} pages, délai {args.delai}s")
    debut = time.time()
    res = crawler(args.url, args.max, args.delai)
    s = res["synthese"]

    # Le netloc peut porter un port (`localhost:8765`) : sous Windows, un `:` dans
    # un nom de fichier cree un flux de donnees alterne NTFS — le fichier semble
    # ecrit et n'existe pas comme fichier. On assainit toujours.
    domaine = re.sub(r"[^A-Za-z0-9.-]+", "-",
                     urllib.parse.urlsplit(res["collecte"]["racine"]).netloc)
    cible = dossier / f"crawl-{domaine}-{dt.date.today():%Y%m%d}.json"
    cible.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nécrit : {cible.relative_to(Path(args.projet).resolve())}")
    print(f"  durée               : {round(time.time() - debut)} s")
    print(f"  pages crawlées      : {s['pages_crawlees']} / {res['collecte']['plafond']}")
    print(f"  URLs découvertes    : {s['urls_decouvertes']}")
    print(f"  profondeur max      : {s['profondeur_max']} clics")
    print(f"  erreurs 4xx/5xx     : {s['erreurs_4xx_5xx']}")
    print(f"  non indexables      : {s['non_indexables']}")
    print(f"  pages orphelines    : {s['pages_orphelines']}")
    print(f"  titles dupliqués    : {s['titles_dupliques']}")
    print(f"  pages < 300 mots    : {s['pages_fines_sous_300_mots']}")
    if not res["collecte"]["robots_txt_lu"]:
        print("  ATTENTION robots.txt illisible — crawl mené sans ses directives")
    if res["collecte"]["urls_bloquees_par_robots"]:
        print(f"  {res['collecte']['urls_bloquees_par_robots']} URL(s) écartée(s) par robots.txt")
    print("\nÉtape suivante : python scripts/livrables.py --projet <chemin>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
