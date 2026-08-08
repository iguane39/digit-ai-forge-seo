"""Gabarit du rapport HTML client — charte, tokens, squelette, composants.

Socle `digit-ai-page-html` (decision D-09) : tokens :root, Roboto titres / DM Sans
corps, theme clair, aucun hex hors :root, WCAG 2.2 AA, lang="fr", un seul <h1>.

Autonomie totale (D-10) : aucun appel reseau. CSS et JS inline, polices en repli
systeme. Le fichier s'ouvre hors ligne, dans deux ans, derriere un proxy.

Ce module ne lit aucune donnee : il ne sait que mettre en forme. La collecte est
dans rapport_html.py.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import html as _html
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Le composant de filtres est installe dans digit-ai-page-html (decision D-12).
# On lit l'asset du skill en priorite ; la copie vendoree reste le repli pour une
# machine ou le skill n'est pas deploye. Le HTML produit est identique dans les
# deux cas -- meme code, meme contrat de marquage.
SKILL_ASSET = (
    Path.home() / ".claude" / "skills" / "digit-ai-page-html" / "assets" / "table-filters.js"
)
VENDOR = RACINE / "assets" / "vendor" / "table-filters.js"


def source_filtres() -> tuple[str, str]:
    """Retourne (code, origine). Origine tracee dans le rapport de generation."""
    if SKILL_ASSET.exists():
        return SKILL_ASSET.read_text(encoding="utf-8"), "digit-ai-page-html"
    if VENDOR.exists():
        return VENDOR.read_text(encoding="utf-8"), "copie vendoree"
    return "", "absent"

# --------------------------------------------------------- niveaux de preuve

# Discriminables SANS dependre de la couleur seule (WCAG) : chaque tier porte un
# glyphe distinct ET un style de bordure distinct. C'est la contrainte centrale du
# livrable -- une mise en forme uniforme rendrait un chiffre infere identique a un
# chiffre mesure, et annulerait tout le dispositif anti-hallucination du skill.
PREUVES = {
    "T1": ("●", "observé", "mesuré directement : crawl, HTTP, HTML, rendu"),
    "T2": ("◐", "déclaré", "export client (GSC / GA / CRM), avec sa période"),
    "T3": ("◔", "tiers", "source nommée, avec URL et date de consultation"),
    "T4": ("○", "inféré", "hypothèse : fourchette et calcul visibles, jamais une prévision"),
    "NM": ("⊘", "non mesuré", "hors de portée en l'état — ce qu'il faut fournir est indiqué"),
}


def esc(valeur) -> str:
    """Echappement systematique. Les fiches peuvent contenir des extraits de pages
    crawlees : injecte tel quel, c'est du XSS dans un document envoye a un client."""
    if valeur is None:
        return ""
    return _html.escape(str(valeur), quote=True)


def badge_preuve(tier: str) -> str:
    tier = (tier or "").upper()
    if tier not in PREUVES:
        return ""
    glyphe, libelle, aide = PREUVES[tier]
    return (
        f'<span class="pv pv-{tier.lower()}" title="{esc(libelle)} — {esc(aide)}">'
        f'<span class="pv-g" aria-hidden="true">{glyphe}</span>'
        f'<span class="pv-t">{esc(tier)}</span>'
        f'<span class="sr">&nbsp;{esc(libelle)}</span></span>'
    )


def legende_preuves() -> str:
    lignes = "".join(
        f'<li>{badge_preuve(t)} <b>{esc(PREUVES[t][1])}</b> — {esc(PREUVES[t][2])}</li>'
        for t in ("T1", "T2", "T3", "T4", "NM")
    )
    return (
        '<aside class="legende" aria-label="Légende des niveaux de preuve">'
        "<h2>Comment lire ce rapport</h2>"
        "<p>Chaque affirmation chiffrée porte son niveau de preuve. "
        "Un chiffre sans marque est une erreur de production, pas une donnée.</p>"
        f'<ul class="pv-legend">{lignes}</ul></aside>'
    )


# ------------------------------------------------------------------- fragments


def absence(titre: str, motif: str, remede: str) -> str:
    """Une absence est une information, pas un vide a masquer."""
    return (
        f'<div class="absence"><p class="abs-t">{badge_preuve("NM")} {esc(titre)}</p>'
        f"<p>{esc(motif)}</p>"
        f'<p class="abs-r"><b>Pour la lever</b> — {esc(remede)}</p></div>'
    )


def section(ident: str, titre: str, corps: str, replie: bool = False) -> str:
    if not replie:
        return f'<section id="{esc(ident)}"><h2>{esc(titre)}</h2>{corps}</section>'
    return (
        f'<section id="{esc(ident)}"><details><summary><h2>{esc(titre)}</h2>'
        f'<span class="chev" aria-hidden="true"></span></summary>'
        f'<div class="det-body">{corps}</div></details></section>'
    )


def tableau(
    ident: str,
    entetes: list[str],
    lignes: list[list[str]],
    libelle: str,
    largeurs: list[int] | None = None,
) -> str:
    """Tableau filtrable. Contrat de marquage du composant partage (D-12) :
    id + thead porteur de th, data-filterable, compteur data-tf-count-for aria-live.

    `largeurs` : repartition en pourcentages. Sans elle, table-layout:fixed donne la
    meme largeur a toutes les colonnes -- une phrase d'action se retrouve a un mot par
    ligne pendant qu'une colonne de score occupe la meme place. Illisible.
    """
    if not lignes:
        return ""
    # Largeurs portees par les <th> plutot que par un groupe de colonnes : ce dernier
    # couvre geometriquement toute la table, donc "chevauche" thead et tbody par
    # construction -- l'oracle V4 le compte, a juste titre puisqu'il ne peut pas savoir
    # que la superposition est structurelle. Sans l'element, pas d'artefact.
    th = "".join(
        f'<th scope="col"'
        + (f' style="width:{largeurs[i]}%"' if largeurs and i < len(largeurs) else "")
        + f">{e}</th>"
        for i, e in enumerate(entetes)
    )
    # data-l porte l'intitule de colonne : c'est lui qui rend la ligne lisible une
    # fois le thead masque, dans le mode carte empilee sous 900px.
    tr = "".join(
        "<tr>"
        + "".join(
            f'<td data-l="{esc(entetes[i] if i < len(entetes) else "")}">{c}</td>'
            for i, c in enumerate(l)
        )
        + "</tr>"
        for l in lignes
    )
    filtrable = " data-filterable" if len(lignes) >= 8 else ""
    compteur = (
        f'<div class="tf-count" data-tf-count-for="{esc(ident)}" aria-live="polite"></div>'
        if filtrable
        else ""
    )
    return (
        f'<div class="tw"><table id="{esc(ident)}"{filtrable}>'
        f"<caption class=\"sr\">{esc(libelle)}</caption>"
        f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>{compteur}"
    )


def barre(valeur: int, maxi: int = 5, libelle: str = "") -> str:
    """Echelle 1-5 lisible sans couleur : carres pleins et vides."""
    try:
        v = int(valeur)
    except (TypeError, ValueError):
        return '<span class="sc sc-na">n/d</span>'
    v = max(0, min(maxi, v))
    plein = "▩" * v
    vide = "▢" * (maxi - v)
    aide = f"{libelle} {v} sur {maxi}" if libelle else f"{v} sur {maxi}"
    return f'<span class="sc" title="{esc(aide)}"><span aria-hidden="true">{plein}{vide}</span><span class="sr">{esc(aide)}</span></span>'


# ------------------------------------------------------------------------- CSS

CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0}

:root{
  --blue:#2563EB; --blue-fill:#EFF4FE; --blue-line:#C9DBFC;
  --bg:#FAFBFF; --surface:#FFFFFF; --card:#FFFFFF;
  --ink:#0F172A; --muted:#475569; --faint:#64748B; --line:#E6EAF2;
  --amber:#B45309; --amber-fill:#FFFBEB; --amber-line:#FDE9C8;
  --teal:#0E7490;  --teal-fill:#EFFDFB;  --teal-line:#C7F0EA;
  --green:#15803D; --green-fill:#F2FCF5; --green-line:#CFEEDD;
  --danger:#B91C1C; --danger-fill:#FEF2F2; --danger-line:#FBD5D5;
  --accent:var(--blue);
  --r:12px; --r-sm:8px;
  --head:"Roboto",system-ui,-apple-system,"Segoe UI",sans-serif;
  --sans:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"Consolas",monospace;
  --w:1080px;
}

body{background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.6}
.wrap{max-width:var(--w);margin:0 auto;padding:28px 20px 64px}
h1,h2,h3,h4{font-family:var(--head);line-height:1.25;margin:0 0 .5em}
h1{font-size:1.9rem;letter-spacing:-.01em}
h2{font-size:1.22rem;margin-top:0}
h3{font-size:1rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
p{margin:0 0 .8em}
a{color:var(--blue)}
code,.mono{font-family:var(--mono);font-size:.88em}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}

/* --- bandeau --- */
.band{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:20px 22px;margin-bottom:20px}
.band .eyebrow{font-family:var(--head);font-size:.72rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 6px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px 18px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}
.meta div{min-width:0}
.meta dt{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint)}
.meta dd{margin:2px 0 0;font-weight:600;overflow-wrap:anywhere}

section{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:20px 22px;margin-bottom:16px}
section>h2,details summary h2{border-left:3px solid var(--accent);padding-left:10px}

details>summary{list-style:none;cursor:pointer;display:flex;align-items:center;
  justify-content:space-between;gap:12px}
details>summary::-webkit-details-marker{display:none}
details summary h2{margin:0}
.chev{width:9px;height:9px;border-right:2px solid var(--faint);
  border-bottom:2px solid var(--faint);transform:rotate(45deg);flex:0 0 auto}
details[open] .chev{transform:rotate(-135deg)}
.det-body{margin-top:16px}

/* --- niveaux de preuve : glyphe + bordure, jamais la couleur seule --- */
.pv{display:inline-flex;align-items:center;gap:4px;font-family:var(--mono);
  font-size:.68rem;font-weight:700;padding:1px 6px;border-radius:var(--r-sm);
  vertical-align:baseline;white-space:nowrap}
.pv-g{font-size:.8em;line-height:1}
.pv-t1{color:var(--green);background:var(--green-fill);border:2px solid var(--green)}
.pv-t2{color:var(--teal);background:var(--teal-fill);border:1px solid var(--teal)}
.pv-t3{color:var(--amber);background:var(--amber-fill);border:1px dashed var(--amber)}
/* Fond uni volontaire : un fond rayé rend le contraste non mesurable par l'oracle,
   or c'est le badge le plus important du rapport. Le glyphe ○ et la bordure
   pointillee suffisent a le discriminer sans dependre de la couleur. */
.pv-t4{color:var(--danger);background:var(--danger-fill);
  border:1px dotted var(--danger)}
.pv-nm{color:var(--faint);background:var(--surface);border:1px dashed var(--faint);
  font-style:italic}
.pv-legend{list-style:none;padding:0;margin:10px 0 0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px 18px}
.pv-legend li{font-size:.85rem;color:var(--muted)}
.legende{background:var(--blue-fill);border:1px solid var(--blue-line);
  border-radius:var(--r);padding:16px 20px;margin-bottom:16px}
.legende h2{border:0;padding:0;font-size:1rem}
.legende p{margin:0;font-size:.88rem;color:var(--muted)}

/* --- repartition des preuves --- */
.repart{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0;padding:0;list-style:none}
.repart li{border:1px solid var(--line);border-radius:var(--r-sm);padding:6px 10px;
  font-size:.8rem;background:var(--bg)}
.repart b{font-family:var(--mono)}

/* --- cartes --- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:14px 16px;break-inside:avoid}
.card h3{margin:0 0 6px}
.kpi{font-family:var(--head);font-size:1.5rem;font-weight:700;line-height:1.1}
.kpi small{display:block;font-size:.72rem;font-weight:400;color:var(--faint);
  text-transform:none;letter-spacing:0;margin-top:4px}

/* --- constats --- */
.constats{list-style:none;padding:0;margin:0}
.constats>li{border:1px solid var(--line);border-left:3px solid var(--line);
  border-radius:var(--r-sm);padding:12px 14px;margin-bottom:10px;break-inside:avoid}
.constats>li.fort{border-left-color:var(--green)}
.constats>li.faible{border-left-color:var(--danger)}
.constats .t{font-weight:600;margin:0 0 4px}
.constats .m{margin:6px 0 0;font-size:.9rem;color:var(--muted)}
.constats .src{margin:6px 0 0;font-size:.78rem;color:var(--faint);font-family:var(--mono);
  overflow-wrap:anywhere}
.trace{font-size:.72rem;color:var(--faint);font-family:var(--mono)}

/* --- tableaux ---
   Pas de defilement horizontal : l'oracle V1 mesure les boites, et un tableau qui
   scrolle deborde quand meme sa boite. On corrige a la source — les cellules
   s'enroulent, et sous 900px chaque ligne devient une carte empilee. */
.tw{border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.85rem;
  background:var(--surface)}
/* Pas de cesure automatique : sur des colonnes etroites elle coupe des mots
   courts en plein milieu — PAYA-NT, MA-NUEL, GRA-TUIT. overflow-wrap suffit
   pour les URLs, qui sont le seul cas ou une coupure est necessaire. */
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);
  vertical-align:top;overflow-wrap:break-word}
td .mono{overflow-wrap:anywhere}
thead th{position:relative;background:var(--bg);font-family:var(--head);
  font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:var(--mono);text-align:right;white-space:nowrap}
.sc{font-family:var(--mono);letter-spacing:-1px;white-space:nowrap}
.sc-na{color:var(--faint);letter-spacing:0}

/* --- filtres (composant partage, styles adaptes aux tokens) --- */
.tf-btn{border:0;background:none;cursor:pointer;font:inherit;color:var(--muted);
  padding:0 0 0 4px}
.tf-btn[aria-expanded="true"],.tf-btn.tf-on{color:var(--accent)}
.tf-panel{position:absolute;z-index:10;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r-sm);padding:8px;
  box-shadow:0 6px 20px rgba(15,23,42,.10);min-width:190px}
.tf-panel[hidden]{display:none}
.tf-opts{max-height:220px;overflow-y:auto;font-size:.8rem;text-transform:none;
  letter-spacing:0}
.tf-opts label{display:block;padding:2px 0;font-weight:400;color:var(--ink)}
.tf-panel input[type=search]{width:100%;margin-bottom:6px;padding:4px 6px;
  border:1px solid var(--line);border-radius:var(--r-sm);font:inherit;font-size:.8rem}
.tf-count{margin-top:4px;font-size:.72rem;color:var(--muted);min-height:1em}
.tf-count.zero{color:var(--danger)}

/* --- matrice gain x effort --- */
.mx{display:grid;grid-template-columns:auto repeat(5,1fr);gap:3px;margin-top:10px;
  font-size:.72rem}
.mx .axl{font-family:var(--head);font-size:.66rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--faint);display:flex;align-items:center;
  justify-content:center;padding:2px}
.mx .cell{background:var(--bg);border:1px solid var(--line);border-radius:var(--r-sm);
  min-height:52px;padding:4px}
.mx .cell.hot{background:var(--green-fill);border-color:var(--green-line)}
.mx .cell.cold{background:var(--danger-fill);border-color:var(--danger-line)}
.mx .chip{display:block;background:var(--surface);border:1px solid var(--line);
  border-radius:4px;padding:1px 4px;margin-bottom:2px;font-family:var(--mono);
  font-size:.66rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.axis-y{writing-mode:vertical-rl;transform:rotate(180deg)}

/* --- quadrants --- */
.quads{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.quad{border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;
  background:var(--card);break-inside:avoid}
.quad h3{margin:0 0 8px;color:var(--ink)}
.quad ol{margin:0;padding-left:18px;font-size:.85rem}
.quad li{margin-bottom:5px}
.quad .cout{font-family:var(--mono);font-size:.72rem;color:var(--muted)}
.warn{background:var(--amber-fill);border:1px solid var(--amber-line);
  border-left:3px solid var(--amber);border-radius:var(--r-sm);padding:12px 14px;
  margin-top:12px;font-size:.88rem}
.warn p{margin:0 0 8px}
.warn p:last-child{margin-bottom:0}
.warn-t{font-family:var(--head);font-weight:700;color:var(--amber)}

/* --- absence declaree --- */
.absence{background:var(--bg);border:1px dashed var(--faint);border-radius:var(--r-sm);
  padding:14px 16px;margin:6px 0}
.absence .abs-t{font-weight:600;margin:0 0 6px;display:flex;align-items:center;gap:6px}
.absence p{font-size:.88rem;color:var(--muted);margin:0 0 6px}
.absence .abs-r{margin:0;color:var(--ink)}

footer.doc{margin-top:24px;padding-top:14px;border-top:1px solid var(--line);
  font-size:.78rem;color:var(--faint)}
.conf{background:var(--danger-fill);border:1px solid var(--danger-line);
  border-radius:var(--r-sm);padding:10px 14px;font-size:.8rem;margin-top:14px}

/* Sous 900px, une ligne devient une carte : chaque cellule porte son intitule via
   data-l. Zero debordement horizontal, et un tableau de 10 colonnes reste lisible
   sur telephone. Contrepartie assumee : les declencheurs de filtre vivent dans le
   thead, donc masques dans ce mode — filtrer 87 lignes sur 375px n'aurait de toute
   facon aucun sens. */
@media (max-width:900px){
  .tw{border:0}
  table{display:block}
  /* Clipper le thead ne suffit pas : chaque th garde sa boite naturelle et deborde
     encore le viewport. On applique le traitement a chaque th — invisible, mais
     toujours dans l'arbre d'accessibilite et lisible par le composant de filtres. */
  thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  /* !important : les largeurs de colonne sont inline sur les th (voir tableau()),
     et une regle de feuille de style ne les surcharge pas sans cela. */
  thead tr,thead th{display:block;width:1px !important;height:1px;overflow:hidden;
    padding:0;border:0;white-space:nowrap}
  tbody,tr,td{display:block;width:auto}
  tr{border:1px solid var(--line);border-radius:var(--r-sm);margin-bottom:8px;
    padding:4px 0;background:var(--surface)}
  td{display:flex;gap:10px;border:0;padding:4px 12px}
  td::before{content:attr(data-l);flex:0 0 38%;color:var(--faint);
    font-family:var(--head);font-size:.68rem;text-transform:uppercase;
    letter-spacing:.04em;line-height:1.5}
  td:empty{display:none}
}

@media (max-width:640px){
  .wrap{padding:16px 12px 40px}
  h1{font-size:1.45rem}
  .mx{font-size:.62rem}
  .mx .cell{min-height:42px}
  .pv-legend{grid-template-columns:1fr}
}

@media print{
  body{background:#fff}
  .wrap{max-width:none;padding:0}
  section,.band,.legende,.card,.quad{break-inside:avoid;box-shadow:none}
  details{display:block}
  details>summary{display:none}
  .det-body{margin-top:0}
  .chev{display:none}
  .tf-btn,.tf-panel{display:none !important}
  tr[data-tf-hidden]{display:table-row !important}
  /* La page imprimee fait ~800px CSS : sans ce retour, le mode carte empilee
     s'appliquerait au papier. On rend au tableau sa forme tabulaire. */
  .tw{border:1px solid var(--line)}
  table{display:table;table-layout:auto}
  thead{position:static;width:auto;height:auto;overflow:visible;clip:auto}
  tbody{display:table-row-group}
  tr{display:table-row;border:0;margin:0;padding:0}
  td{display:table-cell;padding:6px 8px;border-bottom:1px solid var(--line)}
  td::before{content:none}
  td:empty{display:table-cell}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:.7em;color:#555}
}
"""


def page(titre: str, blocs: list[str], pied: str) -> str:
    """Squelette complet. Un seul <h1>, lang fr, viewport, tout inline."""
    js, _origine = source_filtres()
    # initAll() est l'API prevue par le composant, et la seule forme que son oracle
    # reconnait (regle G3). Une boucle querySelectorAll fonctionne au navigateur mais
    # n'est pas analysable statiquement : elle ne prouve rien.
    init = "\nDigitAITableFilters.initAll(document);" if js else ""
    return (
        "<!doctype html>\n"
        '<html lang="fr"><head><meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(titre)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        f'<div class="wrap">\n{"".join(blocs)}\n{pied}\n</div>\n'
        f"<script>{js}{init}</script>\n"
        "</body></html>\n"
    )
