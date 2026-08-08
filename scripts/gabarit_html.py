"""Gabarit du rapport HTML client — charte, tokens, squelette, composants.

Socle `digit-ai-page-html` : tokens :root, Roboto titres / DM Sans corps, theme
clair, aucun hex hors :root, WCAG 2.2 AA, lang="fr", un seul <h1>.

Autonomie totale : aucun appel reseau. CSS et JS inline, polices en repli systeme.
Le fichier s'ouvre hors ligne, dans deux ans, derriere un proxy.

Ce module ne lit aucune donnee : il ne sait que mettre en forme. La collecte est
dans rapport_html.py.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import html as _html
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOCLE = Path.home() / ".claude" / "skills" / "digit-ai-page-html" / "assets"
VENDOR = RACINE / "assets" / "vendor"

# Budgets de densite. Le document doit PARAITRE trois fois plus court et CONTENIR
# deux fois plus : on stratifie, on ne tronque pas.
MOTS_N1 = 12
MOTS_N2 = 60


def _asset(nom: str) -> str:
    """Lit un composant du socle, avec repli sur la copie vendoree."""
    for base in (SOCLE, VENDOR):
        p = base / nom
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def source_filtres() -> tuple[str, str]:
    """Retourne (code, origine) du composant de filtres."""
    if (SOCLE / "table-filters.js").exists():
        return (SOCLE / "table-filters.js").read_text(encoding="utf-8"), "digit-ai-page-html"
    if (VENDOR / "table-filters.js").exists():
        return (VENDOR / "table-filters.js").read_text(encoding="utf-8"), "copie vendoree"
    return "", "absent"


# --------------------------------------------------------- niveaux de preuve

# Discriminables SANS dependre de la couleur seule (WCAG) : chaque tier porte un
# glyphe distinct ET un style de bordure distinct. C'est la contrainte centrale du
# livrable -- une mise en forme uniforme rendrait un chiffre infere identique a un
# chiffre mesure, et annulerait tout le dispositif anti-hallucination.
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


def badge_preuve(tier: str, compact: bool = False) -> str:
    """Le badge reste visible dans TOUTES les vues, y compris compactes."""
    tier = (tier or "").upper()
    if tier not in PREUVES:
        return ""
    glyphe, libelle, aide = PREUVES[tier]
    cl = "pv pv-" + tier.lower() + (" pv-c" if compact else "")
    return (
        f'<span class="{cl}" title="{esc(libelle)} — {esc(aide)}">'
        f'<span class="pv-g" aria-hidden="true">{glyphe}</span>'
        + ("" if compact else f'<span class="pv-t">{esc(tier)}</span>')
        + f'<span class="sr">&nbsp;{esc(tier)} {esc(libelle)}</span></span>'
    )


def legende_preuves() -> str:
    lignes = "".join(
        f"<li>{badge_preuve(t)} <b>{esc(PREUVES[t][1])}</b> — {esc(PREUVES[t][2])}</li>"
        for t in ("T1", "T2", "T3", "T4", "NM")
    )
    return (
        '<aside class="legende" aria-label="Légende des niveaux de preuve">'
        "<h3>Comment lire ce rapport</h3>"
        "<p>Chaque affirmation chiffrée porte son niveau de preuve. "
        "Un chiffre sans marque est une erreur de production, pas une donnée.</p>"
        f'<ul class="pv-legend">{lignes}</ul></aside>'
    )


# ------------------------------------------------------------- stratification


def resume(texte: str, mots: int = MOTS_N1) -> tuple[str, bool]:
    """Niveau 1 : l'essentiel en <= `mots` mots. Retourne (resume, tronque).

    On coupe a la premiere ponctuation forte si elle arrive tot -- une action reelle
    enonce souvent sa proposition avant de detailler apres ':' ou '—'.
    """
    t = (texte or "").strip()
    if not t:
        return "", False
    for sep in (" : ", " — ", " – "):
        i = t.find(sep)
        if 0 < i <= 90:
            tete = t[:i].strip()
            if len(tete.split()) <= mots + 4:
                return tete, True
    lots = t.split()
    if len(lots) <= mots:
        return t, False
    return " ".join(lots[:mots]) + "…", True


def borne(texte: str, mots: int = MOTS_N2) -> str:
    lots = (texte or "").split()
    return " ".join(lots[:mots]) + ("…" if len(lots) > mots else "")


def strate(n1: str, n2_titre: str, n2_corps: list[tuple[str, str]]) -> str:
    """Niveau 1 toujours visible, niveau 2 depliable EN PLACE.

    Pas de ligne inseree : une <tr> supplementaire casserait le composant de filtres,
    qui itere les lignes du tbody.
    """
    lignes = "".join(
        f'<div class="kv"><dt>{esc(k)}</dt><dd>{v}</dd></div>'
        for k, v in n2_corps
        if v
    )
    if not lignes:
        return f'<div class="n1">{n1}</div>'
    return (
        f'<div class="n1">{n1}</div>'
        f'<details class="n2"><summary>{esc(n2_titre)}</summary>'
        f'<dl class="kv-l">{lignes}</dl></details>'
    )


# ------------------------------------------------------------------- fragments


def absence(titre: str, motif: str, cout: str, remede: str) -> str:
    """Une absence est une information : ce qui manque, pourquoi, ce que ça coûte au
    lecteur, et comment la lever."""
    return (
        f'<div class="absence"><p class="abs-t">{badge_preuve("NM")} {esc(titre)}</p>'
        f"<p>{esc(motif)}</p>"
        f'<p class="abs-c"><b>Ce que ça coûte</b> — {esc(cout)}</p>'
        f'<p class="abs-r"><b>Pour la lever</b> — {esc(remede)}</p></div>'
    )


def chapitre(num: int, ident: str, titre: str, corps: str, sous_titre: str = "",
             annexe: str = "") -> str:
    """`annexe` : si fourni, le corps est replie derriere ce libelle.

    Les tables de reference — couverture, inventaire d'URL — sont consultees, pas
    lues. Les laisser ouvertes rallonge le document de plusieurs milliers de pixels
    sans rien apporter au lecteur qui parcourt.
    """
    st = f'<p class="ch-st">{esc(sous_titre)}</p>' if sous_titre else ""
    if annexe:
        corps = (f'<details class="annexe"><summary>{esc(annexe)}</summary>'
                 f'<div class="annexe-c">{corps}</div></details>')
    return (
        f'<section id="{esc(ident)}" class="ch">'
        f'<h2><span class="ch-n">{num}</span>{esc(titre)}</h2>{st}{corps}</section>'
    )


def sommaire(entrees: list[tuple[int, str, str, str]]) -> str:
    """Sommaire collant. `entrees` = (num, ident, titre, compte)."""
    li = "".join(
        f'<li><a href="#{esc(i)}"><span class="toc-n">{n}</span>'
        f'<span class="toc-t">{esc(t)}</span>'
        + (f'<span class="toc-c">{esc(c)}</span>' if c else "")
        + "</a></li>"
        for n, i, t, c in entrees
    )
    return (
        '<nav class="toc" aria-label="Sommaire"><details open><summary>'
        '<span class="toc-h">Sommaire</span>'
        '<span class="toc-x" aria-hidden="true"></span></summary>'
        f"<ol>{li}</ol></details></nav>"
    )


def recherche_globale() -> str:
    return (
        '<div class="find"><label class="sr" for="q">Rechercher dans le document</label>'
        '<input id="q" type="search" placeholder="Rechercher dans tout le rapport…" '
        'autocomplete="off">'
        '<span id="qn" class="find-n" aria-live="polite"></span></div>'
    )


def tableau(
    ident: str,
    colonnes: list[dict],
    lignes: list[list],
    libelle: str,
    groupes: list[tuple[str, int]] | None = None,
    tri_defaut: tuple[int, int] | None = None,
) -> str:
    """Tableau interactif : filtres de colonne, tri, regroupement, filtre texte.

    `colonnes`   : [{'t': intitulé, 'w': largeur %, 'tri': 'num'|'txt'|None}]
    `lignes`     : cellules — str, ou (html, valeur_de_tri)
    `groupes`    : [(libellé, index de colonne)] — clés commutables
    `tri_defaut` : (index, sens), sens 1 croissant / -1 décroissant
    """
    if not lignes:
        return ""

    th = "".join(
        '<th scope="col"'
        + (f' style="width:{c["w"]}%"' if c.get("w") else "")
        + (f' data-tri="{c["tri"]}"' if c.get("tri") else "")
        + f'>{esc(c["t"])}</th>'
        for c in colonnes
    )
    tr = "".join(
        "<tr>"
        + "".join(
            f'<td data-l="{esc(colonnes[i]["t"] if i < len(colonnes) else "")}"'
            + (f' data-v="{esc(c[1])}"' if isinstance(c, tuple) else "")
            + f">{c[0] if isinstance(c, tuple) else c}</td>"
            for i, c in enumerate(l)
        )
        + "</tr>"
        for l in lignes
    )

    filtrable = " data-filterable" if len(lignes) >= 5 else ""
    grp = ""
    if groupes:
        opts = "".join(f'<option value="{i}">{esc(nom)}</option>' for nom, i in groupes)
        grp = (
            '<label class="tb-g">Grouper par '
            f'<select data-groupe-for="{esc(ident)}">'
            f'<option value="">— aucun —</option>{opts}</select></label>'
        )
    tri = f' data-tri-defaut="{tri_defaut[0]},{tri_defaut[1]}"' if tri_defaut else ""

    outils = (
        f'<div class="tb" role="toolbar" aria-label="Outils — {esc(libelle)}">'
        f'<label class="tb-q"><span class="sr">Filtrer {esc(libelle)}</span>'
        f'<input type="search" data-q-for="{esc(ident)}" placeholder="Filtrer ces lignes…" '
        'autocomplete="off"></label>'
        f"{grp}"
        f'<span class="tf-count" data-tf-count-for="{esc(ident)}" aria-live="polite"></span>'
        '<span class="tb-aide">Cliquer un en-tête pour trier</span>'
        "</div>"
    )

    return (
        f"{outils}"
        f'<div class="tw"><table id="{esc(ident)}"{filtrable}{tri}>'
        f'<caption class="sr">{esc(libelle)}</caption>'
        f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>"
    )


def barre(valeur, maxi: int = 5, libelle: str = "") -> str:
    """Echelle 1-5 lisible sans couleur : carres pleins et vides."""
    try:
        v = int(float(valeur))
    except (TypeError, ValueError):
        return '<span class="sc sc-na">n/d</span>'
    v = max(0, min(maxi, v))
    aide = f"{libelle} {v} sur {maxi}" if libelle else f"{v} sur {maxi}"
    return (
        f'<span class="sc" title="{esc(aide)}">'
        f'<span aria-hidden="true">{"▩" * v}{"▢" * (maxi - v)}</span>'
        f'<span class="sr">{esc(aide)}</span></span>'
    )


# ------------------------------------------------------------------------- CSS

CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0}

:root{
  --blue:#2563EB; --blue-fill:#EFF4FE; --blue-line:#C9DBFC;
  --bg:#FAFBFF; --surface:#FFFFFF; --card:#FFFFFF;
  --ink:#0F172A; --muted:#475569; --faint:#64748B; --line:#E6EAF2;
  --amber:#B45309; --amber-fill:#FFFBEB; --amber-line:#FDE9C8;
  --teal:#0E7490;  --teal-fill:#EFFDFB;  --teal-line:#C7F0EA;
  --green:#15803D; --green-fill:#F2FCF5; --green-line:#CFEEDD;
  --danger:#B91C1C; --danger-fill:#FEF2F2; --danger-line:#FBD5D5;
  --mark:#FEF08A;
  --accent:var(--blue);
  --r:12px; --r-sm:8px;
  --head:"Roboto",system-ui,-apple-system,"Segoe UI",sans-serif;
  --sans:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"Consolas",monospace;
  /* Deux largeurs, pas une : un livrable dense a besoin de place pour ses tables,
     une ligne de prose sur 1680px reste illisible. Elargir uniformement
     remplacerait un defaut par un autre. */
  --w:min(92vw,1680px);
  --prose:75ch;
}

body{background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55}
.wrap{max-width:var(--w);margin:0 auto;padding:20px 20px 64px}
h1,h2,h3,h4{font-family:var(--head);line-height:1.22;margin:0 0 .45em}
h1{font-size:1.85rem;letter-spacing:-.01em}
h2{font-size:1.15rem;margin:0 0 .6em;display:flex;align-items:baseline;gap:10px}
h3{font-size:.82rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;
  margin:18px 0 8px}
p{margin:0 0 .7em;max-width:var(--prose)}
li{max-width:var(--prose)}
a{color:var(--blue)}
code,.mono{font-family:var(--mono);font-size:.88em}
mark.find{background:var(--mark);color:inherit;padding:0 1px;border-radius:2px}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}

/* --- bandeau --- */
.band{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:16px 20px;margin-bottom:12px}
.band .eyebrow{font-family:var(--head);font-size:.7rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 4px}
.band h1{max-width:none}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:8px 18px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}
.meta div{min-width:0}
.meta dt{font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint)}
.meta dd{margin:1px 0 0;font-weight:600;overflow-wrap:anywhere;font-size:.9rem}

/* --- barre collante : sommaire + recherche --- */
.sticky{position:sticky;top:0;z-index:40;background:var(--bg);padding:8px 0;
  margin-bottom:12px;border-bottom:1px solid var(--line)}
.sticky-in{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
.toc{flex:1 1 460px;min-width:0}
.toc details{background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r-sm)}
.toc summary{list-style:none;cursor:pointer;padding:7px 12px;display:flex;
  align-items:center;justify-content:space-between}
.toc summary::-webkit-details-marker{display:none}
.toc-h{font-family:var(--head);font-size:.72rem;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted)}
.toc-x{width:8px;height:8px;border-right:2px solid var(--faint);
  border-bottom:2px solid var(--faint);transform:rotate(45deg)}
.toc details[open] .toc-x{transform:rotate(-135deg)}
.toc ol{list-style:none;margin:0;padding:0 8px 8px;display:flex;flex-wrap:wrap;gap:3px}
.toc li{max-width:none}
.toc a{display:flex;align-items:center;gap:5px;text-decoration:none;color:var(--ink);
  font-size:.78rem;padding:3px 8px;border-radius:var(--r-sm);border:1px solid transparent}
.toc a:hover{background:var(--blue-fill);border-color:var(--blue-line)}
.toc-n{font-family:var(--mono);font-size:.68rem;color:var(--faint);min-width:1.1em}
.toc-c{font-family:var(--mono);font-size:.66rem;color:var(--faint)}
.find{flex:0 1 320px;display:flex;flex-direction:column;gap:2px}
.find input{width:100%;padding:7px 10px;border:1px solid var(--line);
  border-radius:var(--r-sm);font:inherit;font-size:.85rem;background:var(--surface)}
.find-n{font-size:.7rem;color:var(--muted);min-height:1em;padding-left:2px}
.find-n.zero{color:var(--danger)}

/* --- chapitres --- */
section.ch{background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);padding:16px 20px;margin-bottom:12px;scroll-margin-top:90px}
section.ch>h2{border-left:3px solid var(--accent);padding-left:10px}
.ch-n{font-family:var(--mono);font-size:.8rem;color:var(--faint)}
.ch-st{color:var(--muted);font-size:.86rem;margin:-4px 0 12px}
details.annexe>summary{list-style:none;cursor:pointer;font-family:var(--head);
  font-size:.78rem;color:var(--accent);display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;border:1px solid var(--blue-line);border-radius:var(--r-sm);
  background:var(--blue-fill)}
details.annexe>summary::-webkit-details-marker{display:none}
details.annexe>summary::before{content:"+";font-family:var(--mono);font-weight:700}
details.annexe[open]>summary::before{content:"−"}
.annexe-c{margin-top:12px}

/* --- niveaux de preuve --- */
.pv{display:inline-flex;align-items:center;gap:3px;font-family:var(--mono);
  font-size:.66rem;font-weight:700;padding:0 5px;border-radius:var(--r-sm);
  vertical-align:baseline;white-space:nowrap}
.pv-c{padding:0 3px}
.pv-g{font-size:.8em;line-height:1}
.pv-t1{color:var(--green);background:var(--green-fill);border:2px solid var(--green)}
.pv-t2{color:var(--teal);background:var(--teal-fill);border:1px solid var(--teal)}
.pv-t3{color:var(--amber);background:var(--amber-fill);border:1px dashed var(--amber)}
.pv-t4{color:var(--danger);background:var(--danger-fill);border:1px dotted var(--danger)}
.pv-nm{color:var(--faint);background:var(--surface);border:1px dashed var(--faint);
  font-style:italic}
.pv-legend{list-style:none;padding:0;margin:8px 0 0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:5px 18px}
.pv-legend li{font-size:.8rem;color:var(--muted);max-width:none}
.legende{background:var(--blue-fill);border:1px solid var(--blue-line);
  border-radius:var(--r-sm);padding:12px 16px;margin:14px 0 0}
.legende h3{margin:0 0 4px;color:var(--ink)}
.legende p{margin:0;font-size:.84rem;color:var(--muted)}

.repart{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0;padding:0;list-style:none}
.repart li{border:1px solid var(--line);border-radius:var(--r-sm);padding:4px 9px;
  font-size:.76rem;background:var(--bg);max-width:none}
.repart b{font-family:var(--mono)}

/* --- cartes --- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:12px 14px;break-inside:avoid}
.card h3{margin:0 0 4px}
.card p{max-width:none}
.kpi{font-family:var(--head);font-size:1.4rem;font-weight:700;line-height:1.1;margin:0}
.kpi small{display:block;font-size:.7rem;font-weight:400;color:var(--faint);
  text-transform:none;letter-spacing:0;margin-top:3px;line-height:1.4}

/* --- synthese --- */
.verdict{background:var(--blue-fill);border:1px solid var(--blue-line);
  border-left:3px solid var(--accent);border-radius:var(--r-sm);padding:12px 16px;
  margin:0 0 14px}
.verdict p{margin:0 0 .4em}
.verdict p:last-child{margin:0}
.top3{list-style:none;padding:0;margin:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px}
.top3 li{border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:var(--r-sm);padding:9px 12px;background:var(--bg);max-width:none}
.top3 .t{font-weight:600;font-size:.88rem;display:block;margin-bottom:3px}
.top3 .m{font-size:.72rem;color:var(--muted);font-family:var(--mono)}

/* --- constats --- */
.constats{list-style:none;padding:0;margin:0}
.constats>li{border:1px solid var(--line);border-left:3px solid var(--line);
  border-radius:var(--r-sm);padding:9px 12px;margin-bottom:7px;break-inside:avoid;
  max-width:none}
.constats>li.fort{border-left-color:var(--green)}
.constats>li.faible{border-left-color:var(--danger)}
.constats .t{font-weight:600;margin:0 0 3px;display:flex;gap:6px;align-items:baseline;
  flex-wrap:wrap}
.trace{font-size:.68rem;color:var(--faint);font-family:var(--mono)}

/* --- stratification --- */
.n1{font-weight:500}
details.n2{margin-top:4px}
details.n2>summary{list-style:none;cursor:pointer;font-size:.72rem;color:var(--accent);
  font-family:var(--head);letter-spacing:.02em;display:inline-flex;align-items:center;
  gap:4px;padding:1px 6px;border:1px solid var(--blue-line);border-radius:var(--r-sm);
  background:var(--blue-fill)}
details.n2>summary::-webkit-details-marker{display:none}
details.n2>summary::before{content:"+";font-family:var(--mono);font-weight:700}
details.n2[open]>summary::before{content:"−"}
.kv-l{margin:6px 0 0;display:grid;gap:4px}
.kv{display:grid;grid-template-columns:minmax(60px,22%) minmax(0,1fr);gap:8px;font-size:.8rem}
.kv dt{color:var(--faint);font-family:var(--head);font-size:.68rem;
  text-transform:uppercase;letter-spacing:.04em;padding-top:2px}
.kv dd{margin:0;color:var(--ink);overflow-wrap:anywhere}

/* --- barre d'outils de tableau --- */
.tb{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin:0 0 6px;
  padding:7px 10px;background:var(--bg);border:1px solid var(--line);
  border-radius:var(--r-sm)}
.tb input[type=search],.tb select{padding:4px 8px;border:1px solid var(--line);
  border-radius:var(--r-sm);font:inherit;font-size:.8rem;background:var(--surface)}
.tb-q input{min-width:190px}
.tb-g{font-size:.76rem;color:var(--muted);display:flex;align-items:center;gap:5px}
.tb-aide{font-size:.68rem;color:var(--faint);margin-left:auto}
.tf-count{font-size:.72rem;color:var(--muted);font-family:var(--mono)}
.tf-count.zero{color:var(--danger)}

/* --- tableaux --- */
.tw{border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.83rem;
  background:var(--surface)}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line);
  vertical-align:top;overflow-wrap:break-word}
td .mono{overflow-wrap:anywhere}
td p{max-width:none}
thead th{position:relative;background:var(--bg);font-family:var(--head);
  font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
thead th[data-tri]{cursor:pointer;user-select:none}
thead th[data-tri]:hover{color:var(--accent)}
thead th[data-tri]::after{content:"↕";font-size:.85em;opacity:.35;margin-left:3px}
thead th[data-sens="1"]::after{content:"↑";opacity:1;color:var(--accent)}
thead th[data-sens="-1"]::after{content:"↓";opacity:1;color:var(--accent)}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--bg)}
/* Etiquette de groupe posee sur la 1re cellule du 1er element de chaque groupe :
   inserer une <tr> casserait le composant de filtres, qui itere les rows. */
td[data-grp]::before{content:attr(data-grp);display:block;margin:2px 0 6px;
  font-family:var(--head);font-size:.68rem;text-transform:uppercase;
  letter-spacing:.06em;color:var(--accent);border-top:2px solid var(--blue-line);
  padding-top:5px}
.num{font-family:var(--mono);white-space:nowrap}
.sc{font-family:var(--mono);letter-spacing:-1px;white-space:nowrap}
.sc-na{color:var(--faint);letter-spacing:0}

/* --- filtres du socle : affordance rendue visible, sans forker le composant --- */
.tf-btn{border:1px solid var(--line);background:var(--surface);cursor:pointer;
  font:inherit;font-family:var(--head);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);padding:1px 5px;border-radius:4px;
  margin-left:5px;white-space:nowrap}
.tf-btn::after{content:" filtrer"}
.tf-btn:hover{border-color:var(--accent);color:var(--accent)}
.tf-btn[aria-expanded="true"],.tf-btn.tf-on{color:var(--surface);
  background:var(--accent);border-color:var(--accent)}
.tf-panel{position:absolute;z-index:30;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r-sm);padding:8px;
  box-shadow:0 6px 20px rgba(15,23,42,.12);min-width:190px}
.tf-panel[hidden]{display:none}
.tf-opts{max-height:220px;overflow-y:auto;font-size:.78rem;text-transform:none;
  letter-spacing:0}
.tf-opts label{display:block;padding:2px 0;font-weight:400;color:var(--ink)}
.tf-panel input[type=search]{width:100%;margin-bottom:6px;padding:4px 6px;
  border:1px solid var(--line);border-radius:var(--r-sm);font:inherit;font-size:.78rem}

/* --- matrice gain x effort --- */
.mx{display:grid;gap:3px;margin-top:8px;font-size:.7rem}
.mx .axl{font-family:var(--head);font-size:.64rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--faint);display:flex;align-items:center;
  justify-content:center;padding:2px;text-align:center}
.mx .cell{background:var(--bg);border:1px solid var(--line);border-radius:var(--r-sm);
  min-height:44px;padding:3px;display:flex;flex-direction:column;gap:2px}
.mx .cell.hot{background:var(--green-fill);border-color:var(--green-line)}
.mx .cell.cold{background:var(--danger-fill);border-color:var(--danger-line)}
.mx .chip{display:block;width:100%;min-width:0;max-width:100%;text-align:left;background:var(--surface);
  border:1px solid var(--line);border-radius:4px;padding:2px 5px;font:inherit;
  font-size:.66rem;cursor:pointer;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;color:var(--ink)}
.mx .chip:hover{border-color:var(--accent);color:var(--accent)}
.mx .chip b{font-family:var(--mono);font-size:.9em;color:var(--faint);margin-right:4px}
.axis-y{writing-mode:vertical-rl;transform:rotate(180deg)}

/* --- quadrants : compteurs ; la liste vit dans la table --- */
.quads{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:10px}
.quad{border:1px solid var(--line);border-radius:var(--r);padding:11px 14px;
  background:var(--card);break-inside:avoid}
.quad h3{margin:0 0 5px;color:var(--ink)}
.quad .q-n{font-family:var(--head);font-size:1.5rem;font-weight:700;line-height:1}
.quad .q-d{font-size:.72rem;color:var(--muted);margin:3px 0 6px}
.quad .q-a{font-size:.74rem;color:var(--faint)}
.quad button{margin-top:7px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r-sm);padding:3px 9px;font:inherit;font-size:.72rem;
  cursor:pointer;color:var(--accent)}
.quad button:hover{border-color:var(--accent)}
.warn{background:var(--amber-fill);border:1px solid var(--amber-line);
  border-left:3px solid var(--amber);border-radius:var(--r-sm);padding:11px 14px;
  margin-top:11px;font-size:.85rem}
.warn p{margin:0 0 6px}
.warn p:last-child{margin:0}
.warn-t{font-family:var(--head);font-weight:700;color:var(--amber)}

/* --- absence declaree --- */
.absence{background:var(--bg);border:1px dashed var(--faint);border-radius:var(--r-sm);
  padding:12px 15px;margin:6px 0}
.absence .abs-t{font-weight:600;margin:0 0 5px;display:flex;align-items:center;gap:6px}
.absence p{font-size:.85rem;color:var(--muted);margin:0 0 5px}
.absence .abs-c,.absence .abs-r{color:var(--ink)}
.absence .abs-r{margin:0}

footer.doc{margin-top:20px;padding-top:12px;border-top:1px solid var(--line);
  font-size:.76rem;color:var(--faint)}
.conf{background:var(--danger-fill);border:1px solid var(--danger-line);
  border-radius:var(--r-sm);padding:9px 13px;font-size:.78rem;margin-top:12px}
.haut{position:fixed;right:16px;bottom:16px;z-index:50;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r);padding:6px 11px;font:inherit;
  font-size:.74rem;cursor:pointer;color:var(--accent);
  box-shadow:0 3px 12px rgba(15,23,42,.10)}

@media (max-width:900px){
  .tw{border:0}
  table{display:block}
  thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  thead tr,thead th{display:block;width:1px !important;height:1px;overflow:hidden;
    padding:0;border:0;white-space:nowrap}
  tbody,tr,td{display:block;width:auto}
  tr{border:1px solid var(--line);border-radius:var(--r-sm);margin-bottom:7px;
    padding:3px 0;background:var(--surface)}
  td{display:flex;gap:9px;border:0;padding:3px 11px}
  td::before{content:attr(data-l);flex:0 0 36%;color:var(--faint);
    font-family:var(--head);font-size:.66rem;text-transform:uppercase;
    letter-spacing:.04em;line-height:1.5}
  td[data-grp]::before{content:attr(data-grp);flex:none;display:block}
  td:empty{display:none}
}
@media (max-width:640px){
  .wrap{padding:12px 10px 40px}
  h1{font-size:1.4rem}
  .mx{font-size:.6rem}
  .mx .cell{min-height:38px}
  .pv-legend{grid-template-columns:1fr}
  .toc ol{max-height:34vh;overflow-y:auto}
  .tb-aide{display:none}
}

@media print{
  body{background:#fff}
  .wrap{max-width:none;padding:0}
  .sticky,.find,.tb,.haut,.quad button{display:none !important}
  section.ch,.band,.legende,.card,.quad{break-inside:avoid;box-shadow:none}
  details{display:block}
  details.n2>summary,details.annexe>summary{display:none}
  .tf-btn,.tf-panel{display:none !important}
  /* Le client imprime ce qu'il croit avoir : ni un filtre ni un tri ne doivent
     amputer le papier. */
  tr[data-tf-hidden]{display:table-row !important}
  tr[data-q-hidden="1"]{display:table-row !important}
  .tw{border:1px solid var(--line)}
  table{display:table;table-layout:auto}
  thead{position:static;width:auto;height:auto;overflow:visible;clip:auto}
  thead tr{display:table-row}
  thead th{display:table-cell;width:auto !important;height:auto;padding:5px 7px;
    white-space:normal}
  tbody{display:table-row-group}
  tr{display:table-row;border:0;margin:0;padding:0}
  td{display:table-cell;padding:5px 7px;border-bottom:1px solid var(--line)}
  td::before{content:none}
  td[data-grp]::before{content:attr(data-grp);display:block}
  td:empty{display:table-cell}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:.7em;color:#555}
}
"""

# --------------------------------------------------------------- JS maison

JS_OUTILS = r"""
/* Outils de tableau : tri, regroupement, filtre texte. Complete le composant de
   filtres du socle sans le remplacer -- et sans jamais inserer de <tr>, ce qui
   casserait son iteration des lignes. */
(function (root) {
  function corps(t) { var b = t.tBodies && t.tBodies[0]; return b ? Array.prototype.slice.call(b.rows) : []; }
  function val(tr, i) {
    var td = tr.cells[i]; if (!td) return '';
    var d = td.getAttribute('data-v');
    return d !== null ? d : (td.textContent || '').trim();
  }
  function nombre(s) { var m = String(s).replace(',', '.').match(/-?\d+(?:\.\d+)?/); return m ? parseFloat(m[0]) : NaN; }
  function sansAccent(s) {
    return (s || '').toLowerCase()
      .replace(/[àâäá]/g, 'a').replace(/[éèêë]/g, 'e')
      .replace(/[îïí]/g, 'i').replace(/[ôöó]/g, 'o')
      .replace(/[ùûüú]/g, 'u').replace(/ç/g, 'c');
  }

  var etats = {};

  function appliquer(t) {
    var e = etats[t.id], rows = corps(t), tb = t.tBodies[0];
    var ths = t.tHead ? Array.prototype.slice.call(t.tHead.rows[0].cells) : [];

    rows.sort(function (a, b) {
      if (e.groupe !== null) {
        var ga = val(a, e.groupe), gb = val(b, e.groupe);
        if (ga !== gb) return ga.localeCompare(gb, 'fr', { numeric: true });
      }
      if (e.tri === null) return 0;
      var typ = ths[e.tri] ? (ths[e.tri].getAttribute('data-tri') || 'txt') : 'txt';
      var x = val(a, e.tri), y = val(b, e.tri);
      if (typ === 'num') {
        var nx = nombre(x), ny = nombre(y);
        if (isNaN(nx) && isNaN(ny)) return 0;
        if (isNaN(nx)) return 1;
        if (isNaN(ny)) return -1;
        return (nx - ny) * e.sens;
      }
      return x.localeCompare(y, 'fr', { numeric: true }) * e.sens;
    });
    rows.forEach(function (r) { tb.appendChild(r); });

    ths.forEach(function (th, i) {
      if (i === e.tri) th.setAttribute('data-sens', String(e.sens));
      else th.removeAttribute('data-sens');
    });

    rows.forEach(function (r) { if (r.cells[0]) r.cells[0].removeAttribute('data-grp'); });
    if (e.groupe !== null) {
      var comptes = {};
      rows.forEach(function (r) { var v = val(r, e.groupe) || '—'; comptes[v] = (comptes[v] || 0) + 1; });
      var prec = null;
      rows.forEach(function (r) {
        var v = val(r, e.groupe) || '—';
        if (v !== prec && r.cells[0]) { r.cells[0].setAttribute('data-grp', v + '  (' + comptes[v] + ')'); prec = v; }
      });
    }
    filtrerTexte(t);
  }

  function filtrerTexte(t) {
    var e = etats[t.id], q = sansAccent(e.q), rows = corps(t), visibles = 0;
    rows.forEach(function (tr) {
      var ok = !q || sansAccent(tr.textContent).indexOf(q) !== -1;
      if (!ok) { tr.setAttribute('data-q-hidden', '1'); tr.style.display = 'none'; }
      else {
        tr.removeAttribute('data-q-hidden');
        if (!tr.hasAttribute('data-tf-hidden')) { tr.style.display = ''; visibles++; }
      }
    });
    var c = document.querySelector('[data-tf-count-for="' + t.id + '"]');
    if (!c) return;
    if (q) {
      c.textContent = visibles + ' / ' + rows.length + ' ligne' + (visibles > 1 ? 's' : '');
      c.classList.toggle('zero', visibles === 0);
    } else { c.textContent = ''; c.classList.remove('zero'); }
  }

  function init(t) {
    if (!t || !t.id || etats[t.id]) return;
    var d = (t.getAttribute('data-tri-defaut') || '').split(',');
    etats[t.id] = {
      tri: d[0] ? parseInt(d[0], 10) : null,
      sens: d[1] ? parseInt(d[1], 10) : -1,
      groupe: null, q: ''
    };
    if (t.tHead) {
      Array.prototype.forEach.call(t.tHead.rows[0].cells, function (th, i) {
        if (!th.getAttribute('data-tri')) return;
        th.setAttribute('tabindex', '0');
        th.setAttribute('role', 'button');
        function bascule() {
          var e = etats[t.id];
          if (e.tri === i) e.sens = -e.sens;
          else { e.tri = i; e.sens = th.getAttribute('data-tri') === 'num' ? -1 : 1; }
          appliquer(t);
        }
        th.addEventListener('click', function (ev) {
          if (ev.target.closest && ev.target.closest('.tf-btn,.tf-panel')) return;
          bascule();
        });
        th.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); bascule(); }
        });
      });
    }
    var sel = document.querySelector('[data-groupe-for="' + t.id + '"]');
    if (sel) sel.addEventListener('change', function () {
      etats[t.id].groupe = sel.value === '' ? null : parseInt(sel.value, 10);
      appliquer(t);
    });
    var q = document.querySelector('[data-q-for="' + t.id + '"]');
    if (q) q.addEventListener('input', function () { etats[t.id].q = q.value; filtrerTexte(t); });
    appliquer(t);
  }

  /* Filtre la table depuis l'exterieur (pastille de matrice, bouton de quadrant) :
     la vue devient un controle de la table, plus un doublon illisible. */
  function cibler(idTable, texte) {
    var t = document.getElementById(idTable);
    var q = document.querySelector('[data-q-for="' + idTable + '"]');
    if (!t || !q || !etats[t.id]) return;
    q.value = texte; etats[t.id].q = texte; filtrerTexte(t);
    t.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function initAll(racine) {
    Array.prototype.forEach.call((racine || document).querySelectorAll('table[id]'), init);
  }

  root.DigitAITableTools = { init: init, initAll: initAll, cibler: cibler };
})(window);

/* Recherche globale : on deplie les <mark> precedents au lieu de reecrire
   innerHTML -- le reset du composant du socle detruirait les ecouteurs des filtres
   et du tri. On reutilise sa regex et son surligneur. */
(function () {
  var input = document.getElementById('q'), cpt = document.getElementById('qn');
  var zone = document.querySelector('.wrap');
  if (!input || !zone || !window.DigitAIFindInPage) return;
  function nettoyer() {
    Array.prototype.forEach.call(zone.querySelectorAll('mark.find'), function (m) {
      var p = m.parentNode; if (!p) return;
      p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
    });
  }
  input.addEventListener('input', function () {
    nettoyer();
    var re = window.DigitAIFindInPage.buildRegex(input.value);
    if (!re) { cpt.textContent = ''; cpt.classList.remove('zero'); return; }
    var n = window.DigitAIFindInPage.highlight(zone, re);
    cpt.textContent = n === 0 ? 'Aucune occurrence' : n + ' occurrence' + (n > 1 ? 's' : '');
    cpt.classList.toggle('zero', n === 0);
  });
})();

/* Sommaire : chapitre courant surligne. */
(function () {
  var liens = Array.prototype.slice.call(document.querySelectorAll('.toc a'));
  if (!liens.length || !('IntersectionObserver' in window)) return;
  var secs = liens.map(function (a) { return document.querySelector(a.getAttribute('href')); });
  var io = new IntersectionObserver(function (ents) {
    ents.forEach(function (e) {
      if (!e.isIntersecting) return;
      var i = secs.indexOf(e.target);
      liens.forEach(function (a, k) { a.style.background = k === i ? 'var(--blue-fill)' : ''; });
    });
  }, { rootMargin: '-80px 0px -70% 0px' });
  secs.forEach(function (s) { if (s) io.observe(s); });
})();
"""


def page(titre: str, blocs: list[str], pied: str) -> str:
    """Squelette complet. Un seul <h1>, lang fr, viewport, tout inline."""
    filtres, _ = source_filtres()
    recherche = _asset("find-in-page.js")
    init = ("\nDigitAITableFilters.initAll(document);" if filtres else "") + (
        "\nDigitAITableTools.initAll(document);"
    )
    js = filtres + "\n" + recherche + "\n" + JS_OUTILS + init
    # `find-in-page.js` documente son cablage en commentaire, avec un `</script>`
    # dedans. Inline tel quel, il TERMINE l'element script : tout ce qui suit est
    # parse comme du HTML et ne s'execute jamais. Le rendu paraissait correct et
    # aucune interaction ne marchait.
    js = js.replace("</script", "<\\/script")
    return (
        "<!doctype html>\n"
        '<html lang="fr"><head><meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(titre)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        f'<div class="wrap">\n{"".join(blocs)}\n{pied}\n</div>\n'
        '<button class="haut" onclick="window.scrollTo({top:0,behavior:\'smooth\'})">'
        "↑ Haut</button>\n"
        f"<script>{js}</script>\n"
        "</body></html>\n"
    )
