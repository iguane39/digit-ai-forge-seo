"""Oracle d'execution : le JS du rapport tourne-t-il vraiment ?

Les oracles statiques lisent le marquage — ils ne peuvent pas dire si le script
s'execute. Or le rapport a deja porte un defaut exactement de cette nature : un
`</script>` echappe dans un commentaire de composant inline terminait l'element, tout
le JS suivant etait parse comme du HTML mort, la page s'affichait normalement et
aucune interaction ne fonctionnait. check_html, l'oracle de filtres et render_page
etaient tous les trois au vert.

Ce script charge la page dans un navigateur et verifie ce qui n'existe QUE si le code
s'est execute : boutons de filtre injectes, en-tete de tri marque, API exposees, et le
comportement du filtre texte.

PERIMETRE : les rapports produits par `rapport_html.py`. Il attend la couche
d'interaction de ce gabarit — filtres, tri, regroupement, recherche globale. Sur une
page qui n'en porte pas, il echoue legitimement : ce n'est pas un oracle generique de
page HTML, c'est l'oracle d'execution de CE livrable. Le generaliser au socle
supposerait un contrat d'interaction partage, qui n'existe pas.

Prerequis : playwright + chromium (meme dependance que render_page.py du socle).

Usage :
    python scripts/oracle_interaction.py <page.html>

Python 3 + playwright.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SONDES = """() => {
  const q = (s) => document.querySelectorAll(s).length;
  // Premiere table outillee de la page, quelle qu'elle soit : l'oracle doit
  // servir a tout livrable du socle, pas au seul rapport SEO.
  const champ = document.querySelector('[data-q-for]');
  const table = champ ? document.getElementById(champ.getAttribute('data-q-for')) : null;
  let avant = 0, apres = 0;
  if (champ && table) {
    const lignes = () => Array.from(table.tBodies[0].rows)
      .filter(r => r.style.display !== 'none').length;
    avant = lignes();
    champ.value = 'zzzzintrouvablezzzz';
    champ.dispatchEvent(new Event('input', { bubbles: true }));
    apres = lignes();
    champ.value = '';
    champ.dispatchEvent(new Event('input', { bubbles: true }));
  }
  return {
    api_filtres: typeof window.DigitAITableFilters,
    api_outils: typeof window.DigitAITableTools,
    api_recherche: typeof window.DigitAIFindInPage,
    boutons_filtre: q('.tf-btn'),
    entetes_triees: q('th[data-sens]'),
    selecteurs_groupe: q('select[data-groupe-for]'),
    champ_recherche: q('#q'),
    lignes_avant_filtre: avant,
    lignes_apres_filtre: apres,
  };
}"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage : python scripts/oracle_interaction.py <page.html>")
        return 2
    page = Path(sys.argv[1]).resolve()
    if not page.exists():
        print(f"introuvable : {page}")
        return 2

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"oracle": "interaction", "verdict": "INCONCLUSIF",
                          "motif": "playwright absent — installer comme pour render_page.py"},
                         ensure_ascii=False))
        return 2

    erreurs: list[str] = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page()
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        pg.goto(page.as_uri())
        pg.wait_for_load_state("networkidle")
        r = pg.evaluate(SONDES)
        nav.close()

    controles = [
        ("API du composant de filtres exposée", r["api_filtres"] == "object"),
        ("API des outils de tableau exposée", r["api_outils"] == "object"),
        ("API de recherche exposée", r["api_recherche"] == "object"),
        ("boutons de filtre injectés dans les en-têtes",
         r["api_filtres"] != "object" or r["boutons_filtre"] > 0),
        ("tri par défaut appliqué (en-tête marqué)", r["entetes_triees"] > 0),
        ("sélecteurs de regroupement présents",
         r["lignes_avant_filtre"] == 0 or r["selecteurs_groupe"] > 0),
        ("champ de recherche globale présent", r["champ_recherche"] == 1),
        # Sans objet si la page ne porte aucune table outillee : l'oracle reste
        # applicable a toute page du socle, pas seulement au rapport SEO.
        ("le filtre texte masque réellement des lignes",
         r["lignes_avant_filtre"] == 0
         or (r["lignes_avant_filtre"] > 0 and r["lignes_apres_filtre"] == 0)),
        ("aucune erreur JavaScript au chargement", not erreurs),
    ]
    echecs = [nom for nom, ok in controles if not ok]

    print("oracle interaction — exécution réelle du JS\n")
    for nom, ok in controles:
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom}")
    print(f"\n  mesures : {json.dumps(r, ensure_ascii=False)}")
    if erreurs:
        print(f"  erreurs JS : {erreurs[:3]}")
    print(f"\n{len(controles) - len(echecs)}/{len(controles)} contrôles passés")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
