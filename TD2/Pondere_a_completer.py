import sys
import random
import math
import heapq
from collections import deque
import pygame

# ============================================================
# 0) IMPORTS & DÉPENDANCES
# ============================================================
"""
Imports :
- sys : fermeture propre (sys.exit) après pygame.quit()
- random : bruit/texture des tuiles + génération des coûts par case (seed stable)
- math : sqrt pour le brouillard “spotlight”
- heapq : file de priorité (min-heap) pour A* (open set)
- deque : historique borné (panneau droit)
- pygame : rendu 2D, événements clavier, surfaces, fonts, timing

Bonnes pratiques :
- heapq ne supporte pas decrease-key :
    -> on repousse des entrées (f,g,node) et on purge les obsolètes à l'extraction
- seed fixe -> visualisation reproductible
- imports standard -> imports externes (pygame)
"""

# ============================================================
# 1) PARAMÈTRES GÉNÉRAUX
# ============================================================
"""
Ce fichier contient une visualisation A* pondéré (Weighted A*) sur un labyrinthe,
avec une interface Pygame (UI moderne + brouillard + animation d'un pingouin).

Objectifs pédagogiques :
- Visualiser l'exploration A* pas à pas (open/closed, noeud courant, g/h/f).
- Montrer l'impact du poids w sur la "gloutonnerie" de la recherche.
- Afficher les coûts d'entrée des cases, l'heuristique, et le score f_w = g + w*h.
- Illustrer les “rebroussements” du pingouin quand il rejoint le noeud courant.

Convention :
- (r, c) représente une case de grille : r = ligne, c = colonne
- Les temps sont en millisecondes (ms)
- Les positions pixel sont dérivées via TAILLE_CASE et offsets UI

Convention labyrinthe :
- '#' mur (non traversable)
- '.' sol traversable
- 'S' départ
- 'E' sortie

IMPORTANT (pédagogie) :
- A* standard : w = 1.0 -> f = g + h (optimal si h admissible)
- Weighted A* : w > 1 -> f_w = g + w*h
  => souvent plus rapide (moins d'exploration) mais plus forcément optimal en coût.
- Le coût est ici un coût d’ENTRÉE dans une case.
"""

LABYRINTHE = [
    "#######################",
    "#S#.......#...........#",
    "#.#.#####.#.#####.###.#",
    "#.#.....#.......#...#.#",
    "#.#####.#.###.#.###.#.#",
    "#.....#.#...#.#.....#.#",
    "###.#.#.###.#.#####.#.#",
    "#...#.#.....#.....#.#E#",
    "#.###.###########.#.###",
    "#.....................#",
    "#######################",
]

TAILLE_CASE = 40
FPS = 60

# Vitesses d'animation (ms)
ASTAR_EVENT_MS = 260      # cadence des étapes algo en auto
PAS_ROUTE_MS = 70         # déplacement pingouin vers la case courante (algo)
PAS_CHEMIN_MS = 90        # déplacement pingouin sur chemin "solution"
ANIM_PINGOUIN_MS = 140    # cadence animation sprite pingouin

# UI
HAUT_BAR_H = 34
BAS_BAR_H = 72
PANNEAU_DROIT_W = 320
LIGNES_HISTO = 6

# ============================================================
# 2) THEME "MODERNE" (couleurs)
# ============================================================

COL_FOND = (10, 12, 16)

# Panneaux UI
COL_PANEL = (20, 22, 30)
COL_PANEL_BORD = (90, 95, 110)

# Sol / murs
COL_SOL_1 = (78, 84, 104)
COL_SOL_2 = (70, 76, 96)
COL_MUR = (18, 20, 26)
COL_MUR_HI = (38, 41, 52)
COL_MUR_SH = (8, 9, 12)
COL_GRILLE = (105, 112, 135)

# Overlays algo (RGBA)
COL_VISITE = (110, 220, 255, 150)        # closed set (exploré)
COL_A_EXPLORER = (255, 220, 120, 160)    # open set (frontière)
COL_COURANT = (120, 175, 255, 190)       # noeud extrait

COL_CHEMIN_OPT = (160, 255, 190, 170)    # chemin affiché (vert)
COL_REBROUSSE = (210, 165, 255, 130)     # rebroussement (violet)

# Texte
COL_TEXTE = (245, 245, 245)
COL_TEXTE_MUET = (180, 185, 205)
COL_OMBRE = (0, 0, 0)

# Brouillard (base)
ALPHA_FOG_INCONNU = 215
ALPHA_FOG_CONNU = 110

# Brouillard "smooth" (spotlight)
RAYON_LUMIERE_CASES = 3.2
RAYON_FONDU_CASES = 7.0
ALPHA_MIN_SPOT = 0

# Numéros (ordre de passage pingouin)
COL_NUM = (235, 235, 240)

# Coûts affichés dans les cases (haut-droite) -> ROUGE
COL_COUT = (255, 70, 70)

# Heuristique h affichée en bas à droite -> NOIR
COL_H = (0, 0, 0)

# Start/Exit
COL_DEPART = (70, 210, 120)
COL_SORTIE = (255, 105, 105)

# ============================================================
# 3) OUTILS GRILLE
# ============================================================

def hauteur(grille):
    """
    Calcule le nombre de lignes de la grille.

    Args:
        grille (list[str]): grille (liste de chaînes).

    Returns:
        int: nombre de lignes.
    """
    return len(grille)

def largeur(grille):
    """
    Calcule le nombre de colonnes de la grille.

    Hypothèse:
        - Toutes les lignes ont la même longueur.

    Args:
        grille (list[str]): grille (liste de chaînes).

    Returns:
        int: nombre de colonnes.
    """
    return len(grille[0])

def trouver_case(grille, caractere):
    """
    Cherche la première occurrence d'un caractère dans la grille.

    Args:
        grille (list[str]): grille de caractères.
        caractere (str): caractère recherché (ex: 'S' ou 'E').

    Returns:
        tuple[int, int] | None: coordonnées (r, c) si trouvé, sinon None.
    """
    for r, ligne in enumerate(grille):
        for c, ch in enumerate(ligne):
            if ch == caractere:
                return (r, c)
    return None

def dans_grille(grille, r, c):
    """
    Vérifie si (r, c) est dans les bornes de la grille.

    Args:
        grille (list[str]): grille.
        r (int): ligne.
        c (int): colonne.

    Returns:
        bool: True si dans la grille, sinon False.
    """
    return 0 <= r < hauteur(grille) and 0 <= c < largeur(grille)

def est_traversable(grille, r, c):
    """
    Indique si une case est traversable (≠ mur '#').

    Args:
        grille (list[str]): grille.
        r (int): ligne.
        c (int): colonne.

    Returns:
        bool: True si traversable, sinon False.
    """
    return grille[r][c] != "#"

def nom_direction(a, b):
    """
    Donne le nom de la direction orthogonale de a vers b.

    Args:
        a (tuple[int,int]): case source (r, c).
        b (tuple[int,int]): case destination (r, c) (voisine de a).

    Returns:
        str | None: "Haut"|"Bas"|"Gauche"|"Droite" si adjacent, sinon None.
    """
    (r1, c1), (r2, c2) = a, b
    dr, dc = r2 - r1, c2 - c1
    if dr == -1 and dc == 0: return "Haut"
    if dr == 1 and dc == 0: return "Bas"
    if dr == 0 and dc == -1: return "Gauche"
    if dr == 0 and dc == 1: return "Droite"
    return None

def direction_opposee(d):
    """
    Renvoie la direction opposée.

    Args:
        d (str): "Haut"|"Bas"|"Gauche"|"Droite".

    Returns:
        str | None: direction opposée, ou None si d inconnu.
    """
    return {"Haut": "Bas", "Bas": "Haut", "Gauche": "Droite", "Droite": "Gauche"}.get(d)

def voisins_4(grille, r, c):
    """
    Génère les voisins 4-connexes traversables.

    IMPORTANT:
        L'ordre est CONTRACTUEL (impacte les égalités / l'ordre d'exploration) :
        Haut, Bas, Gauche, Droite.

    Args:
        grille (list[str]): grille.
        r (int): ligne.
        c (int): colonne.

    Yields:
        tuple[int,int,str]: (rr, cc, nom_direction)
    """
    for dr, dc, nom in [(-1, 0, "Haut"), (1, 0, "Bas"), (0, -1, "Gauche"), (0, 1, "Droite")]:
        rr, cc = r + dr, c + dc
        if dans_grille(grille, rr, cc) and est_traversable(grille, rr, cc):
            yield (rr, cc, nom)

# ============================================================
# 4) A* PONDÉRÉ (Weighted A*)
#    priorité = f_w(n) = g(n) + w * h(n)
# ============================================================
"""
A* standard :
- f(n) = g(n) + h(n)
- si h admissible/consistante -> chemin optimal (en coût)

Weighted A* :
- f_w(n) = g(n) + w*h(n), avec w > 1
- + w est grand -> + on favorise l'heuristique -> + "glouton"
- résultat : souvent + rapide, mais chemin pas garanti optimal (en coût)

Notes d'implémentation :
- open set = heapq de tuples (f, g, node)
- closed set = etat["visite"]
- "frontiere" est un set séparé uniquement pour l'UI
- on gère les entrées obsolètes dans le heap (pas de decrease-key)
"""

def cout_case(couts, pos):
    """
    Retourne le coût d'entrée dans une case.

    Convention :
        - Le coût est payé quand on ENTRE dans une case.
        - Si absent, on considère un coût 1 (par défaut).

    Args:
        couts (dict[tuple[int,int], int]): coût d'entrée par case.
        pos (tuple[int,int]): position (r,c).

    Returns:
        int: coût d'entrée (>=1).
    """
    return couts.get(pos, 1)

def heuristique_manhattan(a, b):
    """
    Heuristique Manhattan (grille 4-connexe).

    Args:
        a (tuple[int,int]): position courante.
        b (tuple[int,int]): objectif.

    Returns:
        int: |dr| + |dc|
    """
    (r1, c1) = a
    (r2, c2) = b
    return abs(r1 - r2) + abs(c1 - c2)

def astar_initialiser(depart, arrivee, w):
    """
    Initialise l'état pour l'exécution incrémentale de Weighted A*.

    L'état contient :
    - pq : heap (f, g, node)
    - visite : closed set
    - frontiere : open set (UI)
    - parent : parents pour reconstruire un chemin
    - g : meilleurs coûts connus (g-score)
    - courant : noeud extrait à l'étape courante
    - termine/trouve : flags d'arrêt
    - w : poids heuristique

    Args:
        depart (tuple[int,int]): case départ.
        arrivee (tuple[int,int]): case but.
        w (float): poids heuristique (w=1 -> A* standard).

    Returns:
        dict: état mutable de l'algorithme.
    """
    pq = []
    g = {depart: 0}
    parent = {depart: None}
    h = heuristique_manhattan(depart, arrivee)
    # weighted A* : f = g + w * h
    f = 0 + w * h
    heapq.heappush(pq, (f, 0, depart))

    etat = {
        "pq": pq,
        "visite": set(),
        "frontiere": {depart},
        "parent": parent,
        "g": g,
        "courant": None,
        "termine": False,
        "trouve": False,
        "w": w,
    }
    return etat

def astar_faire_une_etape(grille, etat, arrivee, couts):
    """
    TODO(3) : Exécuter UNE étape de A*.

    À faire :
    1) Si etat["termine"] : return
    2) Purge entrées périmées dans pq (tant que pq non vide) :
       - si node déjà dans etat["visite"] -> pop et continue
       - si gcur != etat["g"].get(node) -> pop et continue
       - sinon stop purge
    3) Si pq vide :
       - etat["termine"]=True ; etat["trouve"]=False ; etat["courant"]=None ; frontiere.clear()
       - return
    4) Pop du meilleur tuple (fcur, gcur, courant)
       - frontiere.discard(courant)
       - courant devient etat["courant"]
       - visite.add(courant)
    5) Si courant == arrivee :
       - termine=True, trouve=True
       - return
    6) Relaxation voisins :
       - pour chaque voisin traversable nxt:
           - si nxt in visite : continue
           - new_g = gcur + cout_case(couts, nxt)
           - si new_g < etat["g"].get(nxt, inf):
               - etat["g"][nxt] = new_g
               - etat["parent"][nxt] = courant
               - h = heuristique_manhattan(nxt, arrivee)
               - new_f = new_g + h
               - push (new_f, new_g, nxt)
               - frontiere.add(nxt)

    Args:
        grille (list[str])
        etat (dict) : état A*
        arrivee (tuple[int,int])
        couts (dict)

    Returns:
        None (effet de bord sur etat)
    """
    if etat["termine"]:
        return

    pq = etat["pq"]
    visite = etat["visite"]
    frontiere = etat["frontiere"]
    g = etat["g"]
    parent = etat["parent"]
    w = etat["w"]

    # purger les entrees perimees
    while len(pq) > 0:
        f_top, g_top, node_top = pq[0]
        if node_top in visite:
            heapq.heappop(pq)
            continue
        if g_top != g.get(node_top):
            heapq.heappop(pq)
            continue
        break

    # si la pq est vide
    if len(pq) == 0:
        etat["termine"] = True
        etat["trouve"] = False
        etat["courant"] = None
        frontiere.clear()
        return

    # extraire le meilleur noeud
    f_cur, g_cur, courant = heapq.heappop(pq)
    frontiere.discard(courant)
    visite.add(courant)
    etat["courant"] = courant

    # test arrivee
    if courant == arrivee:
        etat["termine"] = True
        etat["trouve"] = True
        return

    # relaxer les voisins
    r, c = courant
    for rr, cc, nom in voisins_4(grille, r, c):
        nxt = (rr, cc)
        if nxt in visite:
            continue
        new_g = g_cur + cout_case(couts, nxt)
        if new_g < g.get(nxt, float("inf")):
            g[nxt] = new_g
            parent[nxt] = courant
            h = heuristique_manhattan(nxt, arrivee)
            # weighted A* : f = g + w * h
            new_f = new_g + w * h
            heapq.heappush(pq, (new_f, new_g, nxt))
            frontiere.add(nxt)


def reconstruire_chemin(parent, depart, arrivee):
    """
    Reconstruire le chemin depuis arrivee en remontant parent[].

    Args:
        parent (dict)
        depart (tuple[int,int])
        arrivee (tuple[int,int])

    Returns:
        list[tuple[int,int]] | None
    """
    if arrivee not in parent:
        return None

    chemin = []
    courant = arrivee
    while courant is not None:
        chemin.append(courant)
        courant = parent.get(courant)

    chemin.reverse()

    if chemin[0] != depart:
        return None

    return chemin

# ============================================================
# 5) PINGOUIN (SPRITES DESSINÉS)
# ============================================================

def creer_frames_pingouin(taille):
    """
    Génère des sprites Pygame (surfaces) pour un pingouin animé.

    Structure:
        frames[direction][frame]
        - direction: 0=haut, 1=droite, 2=bas, 3=gauche
        - frame: 0..3 (variation marche)

    Notes:
        - Dessin vectoriel via primitives Pygame (ellipse, circle, polygon)
        - Les dimensions sont en pixels.

    Args:
        taille (int): taille d'une frame carrée (px).

    Returns:
        list[list[pygame.Surface]]: matrice 4x4 de surfaces avec canal alpha.
    """
    frames = [[None] * 4 for _ in range(4)]
    for d in range(4):
        for i in range(4):
            surf = pygame.Surface((taille, taille), pygame.SRCALPHA)

            # Ombre portée au sol (ellipse semi-transparente)
            pygame.draw.ellipse(
                surf, (0, 0, 0, 70),
                (int(taille * 0.18), int(taille * 0.82), int(taille * 0.64), int(taille * 0.16))
            )

            # Corps + ventre
            corps = pygame.Rect(int(taille * 0.24), int(taille * 0.22), int(taille * 0.52), int(taille * 0.62))
            pygame.draw.ellipse(surf, (25, 30, 40), corps)
            ventre = pygame.Rect(int(taille * 0.30), int(taille * 0.35), int(taille * 0.40), int(taille * 0.42))
            pygame.draw.ellipse(surf, (235, 235, 235), ventre)

            # Tête
            pygame.draw.circle(surf, (25, 30, 40), (int(taille * 0.5), int(taille * 0.26)), int(taille * 0.20))

            # Yeux
            pygame.draw.circle(surf, (245, 245, 245), (int(taille * 0.44), int(taille * 0.24)), int(taille * 0.04))
            pygame.draw.circle(surf, (245, 245, 245), (int(taille * 0.56), int(taille * 0.24)), int(taille * 0.04))
            pygame.draw.circle(surf, (20, 20, 20), (int(taille * 0.44), int(taille * 0.24)), int(taille * 0.02))
            pygame.draw.circle(surf, (20, 20, 20), (int(taille * 0.56), int(taille * 0.24)), int(taille * 0.02))

            # Bec orienté selon la direction
            cx, cy = int(taille * 0.5), int(taille * 0.30)
            s = int(taille * 0.08)
            if d == 0:
                bec = [(cx, cy - s), (cx - s, cy), (cx + s, cy)]
            elif d == 1:
                bec = [(cx + s, cy), (cx, cy - s), (cx, cy + s)]
            elif d == 2:
                bec = [(cx, cy + s), (cx - s, cy), (cx + s, cy)]
            else:
                bec = [(cx - s, cy), (cx, cy - s), (cx, cy + s)]
            pygame.draw.polygon(surf, (240, 180, 70), bec)

            # Pieds (petit décalage alterné pour simuler la marche)
            pieds_y = int(taille * 0.76)
            shift = 2 if (i % 2 == 0) else -2
            pygame.draw.ellipse(
                surf, (240, 180, 70),
                (int(taille * 0.34), pieds_y + shift, int(taille * 0.14), int(taille * 0.08))
            )
            pygame.draw.ellipse(
                surf, (240, 180, 70),
                (int(taille * 0.52), pieds_y - shift, int(taille * 0.14), int(taille * 0.08))
            )

            frames[d][i] = surf
    return frames

# ============================================================
# 6) ROUTE DANS L'ARBRE PARENT (LCA + rebroussement)
# ============================================================
"""
But :
- L'algo A* “saute” de noeud courant en noeud courant.
- Pour une animation “physique”, le pingouin doit se déplacer sur la grille
  jusqu'au noeud courant en suivant l'arbre parent.
- On autorise le rebroussement :
  pingouin remonte vers un ancêtre commun puis redescend.

Technique :
- Calcul du LCA (Lowest Common Ancestor) dans l'arbre parent.
- Retourne full = chemin A->B via LCA
- up_len = taille de la portion “montée” (A->LCA incluse)
"""

def route_dans_arbre_parent_detail(parent, a, b):
    """
    Calcule un chemin de A vers B en utilisant uniquement l'arbre 'parent'.

    Objectif :
        Permettre au pingouin de “rejoindre” la case courante de l'algorithme
        en remontant vers un ancêtre commun puis en redescendant.

    Args:
        parent (dict): mapping {node: parent_node}.
        a (tuple[int,int]): point de départ (position pingouin).
        b (tuple[int,int]): point d'arrivée (noeud courant de l'algo).

    Returns:
        tuple[list[tuple[int,int]], int]:
            - full : chemin complet A->B (liste de noeuds)
            - up_len : nb de noeuds dans la partie “montée” A->LCA incluse

    Notes :
        - Si aucun ancêtre commun n'est trouvé (cas anormal si parent cohérent),
          la fonction renvoie ([b], 1).
    """
    if a == b:
        return [a], 1

    ancetres_a = set()
    cur = a
    while cur is not None and cur in parent:
        ancetres_a.add(cur)
        cur = parent[cur]

    cur = b
    chaine_b = []
    while cur is not None and cur in parent:
        if cur in ancetres_a:
            lca = cur
            break
        chaine_b.append(cur)
        cur = parent[cur]
    else:
        # Cas de secours : parent incohérent / pas de lien
        return [b], 1

    chemin_a = []
    cur = a
    while cur != lca:
        chemin_a.append(cur)
        cur = parent[cur]
    chemin_a.append(lca)

    full = chemin_a + list(reversed(chaine_b))
    up_len = len(chemin_a)
    return full, up_len

# ============================================================
# 7) OUTILS DESSIN MODERNE
# ============================================================

def creer_tuile_bruitee(taille, base1, base2, force=10, seed=0):
    """
    Crée une tuile “texturée” (bruit simple) pour donner du relief visuel au sol.

    Args:
        taille (int): taille de la tuile en pixels.
        base1 (tuple[int,int,int]): couleur de fond.
        base2 (tuple[int,int,int]): couleur de base pour bruit.
        force (int): amplitude max de variation par canal (±force).
        seed (int): graine RNG pour reproductibilité.

    Returns:
        pygame.Surface: surface convertie (performances) de taille (taille, taille).
    """
    rnd = random.Random(seed)
    s = pygame.Surface((taille, taille))
    s.fill(base1)
    for _ in range(30):
        x = rnd.randrange(taille)
        y = rnd.randrange(taille)
        c = rnd.randrange(-force, force + 1)
        col = (
            max(0, min(255, base2[0] + c)),
            max(0, min(255, base2[1] + c)),
            max(0, min(255, base2[2] + c)),
        )
        s.set_at((x, y), col)
    return s.convert()

def dessiner_rect_bevel(surface, rect, fill, hi, sh, radius=7):
    """
    Dessine un rectangle avec effet “bevel” (relief) :
    - bord haut/gauche éclairci (hi)
    - bord bas/droite ombré (sh)

    Args:
        surface (pygame.Surface): surface cible.
        rect (pygame.Rect): zone à dessiner.
        fill (tuple[int,int,int]): couleur principale.
        hi (tuple[int,int,int]): highlight.
        sh (tuple[int,int,int]): shadow.
        radius (int): rayon arrondi.

    Returns:
        None
    """
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.line(surface, hi, (rect.left + radius, rect.top + 1), (rect.right - radius, rect.top + 1), 2)
    pygame.draw.line(surface, hi, (rect.left + 1, rect.top + radius), (rect.left + 1, rect.bottom - radius), 2)
    pygame.draw.line(surface, sh, (rect.left + radius, rect.bottom - 2), (rect.right - radius, rect.bottom - 2), 2)
    pygame.draw.line(surface, sh, (rect.right - 2, rect.top + radius), (rect.right - 2, rect.bottom - radius), 2)

def dessiner_overlay_rgba(ecran, rect, rgba, radius=7, outline=None):
    """
    Dessine un overlay semi-transparent (RGBA) sur une case.

    Implémentation:
        Crée une surface temporaire en SRCALPHA (alpha par pixel),
        puis la blitte sur l'écran.

    Args:
        ecran (pygame.Surface): surface cible.
        rect (pygame.Rect): zone de l'overlay.
        rgba (tuple[int,int,int,int]): couleur + alpha.
        radius (int): arrondi.
        outline (tuple[int,int,int,int] | None): contour optionnel.

    Returns:
        None
    """
    o = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(o, rgba, pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
    if outline:
        pygame.draw.rect(o, outline, pygame.Rect(1, 1, rect.w - 2, rect.h - 2), 2, border_radius=radius)
    ecran.blit(o, rect.topleft)

def dessiner_glow(ecran, centre, couleur_rgb, r1, r2, alpha1=90, alpha2=0):
    """
    Dessine un halo (glow) radial par superposition de cercles alpha.

    Args:
        ecran (pygame.Surface): surface cible.
        centre (tuple[int,int]): centre du glow (px).
        couleur_rgb (tuple[int,int,int]): couleur.
        r1 (int): rayon interne.
        r2 (int): rayon externe.
        alpha1 (int): alpha au rayon r1.
        alpha2 (int): alpha au rayon r2.

    Returns:
        None
    """
    for r in range(r2, r1 - 1, -3):
        t = 1.0 if r2 == r1 else (r - r1) / (r2 - r1)
        a = int(alpha1 * (1 - t) + alpha2 * t)
        g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(g, (*couleur_rgb, a), (r, r), r)
        ecran.blit(g, (centre[0] - r, centre[1] - r))

# ============================================================
# 7bis) FENÊTRE PYGAME POUR CHOISIR w (au lancement)
# ============================================================

def demander_w_pygame(default=1.8):
    """
    Petite fenêtre Pygame qui demande w au lancement.

    Entrées :
    - Tape un nombre (ex: 1, 1.5, 2.0, 3)
    - Entrée : valide
    - Backspace : effacer
    - Échap : annule et prend le défaut

    Args:
        default (float): valeur par défaut si saisie vide ou ESC.

    Returns:
        float: poids w (>0).
    """
    pygame.init()
    pygame.display.set_caption("Choisir w (A* pondéré)")
    W, H = 760, 260
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 22)
    font_small = pygame.font.SysFont("consolas", 16)

    text = ""   # saisie utilisateur
    info = ""   # message erreur
    blink = 0   # curseur clignotant

    def parse_or_none(s):
        """
        Parse la saisie en float strictement positif.
        Tolère la virgule (remplacée par un point).

        Args:
            s (str): saisie brute.

        Returns:
            float | None: valeur > 0 si parsable, sinon None.
        """
        try:
            s2 = s.strip().replace(",", ".")
            if not s2:
                return None
            v = float(s2)
            if v <= 0:
                return None
            return v
        except Exception:
            return None

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.display.quit()
                    return float(default)

                if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
                    v = parse_or_none(text)
                    if v is None:
                        if text.strip() == "":
                            pygame.display.quit()
                            return float(default)
                        info = "Valeur invalide. Exemple: 1, 1.5, 2.0 (w > 0)"
                    else:
                        pygame.display.quit()
                        return float(v)

                if ev.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    ch = ev.unicode
                    # autoriser chiffres, point, virgule
                    if ch.isdigit() or ch in [".", ","]:
                        # empêcher 2 séparateurs
                        if ch in [".", ","] and (("." in text) or ("," in text)):
                            pass
                        else:
                            text += ch

        # ---- rendu fenêtre ----
        screen.fill(COL_FOND)

        panel = pygame.Rect(20, 20, W - 40, H - 40)
        pygame.draw.rect(screen, COL_PANEL, panel, border_radius=10)
        pygame.draw.rect(screen, COL_PANEL_BORD, panel, 2, border_radius=10)

        title = font.render("Choisis le poids w pour A* pondéré", True, COL_TEXTE)
        screen.blit(title, (40, 40))

        hint1 = font_small.render(
            "w = 1.0 => A* standard.  w > 1 => plus glouton (souvent + rapide).",
            True, COL_TEXTE_MUET
        )
        screen.blit(hint1, (40, 75))

        hint2 = font_small.render(
            "Tape un chiffre puis entrée. ESC => défaut. (Défaut: %.2f)" % float(default),
            True, COL_TEXTE_MUET
        )
        screen.blit(hint2, (40, 95))

        box = pygame.Rect(40, 130, W - 80, 52)
        pygame.draw.rect(screen, (28, 32, 42), box, border_radius=10)
        pygame.draw.rect(screen, COL_PANEL_BORD, box, 2, border_radius=10)

        blink = (blink + 1) % 60
        cursor = "|" if blink < 30 else " "
        shown = text if text else ""
        value_txt = font.render(f"w = {shown}{cursor}", True, COL_TEXTE)
        screen.blit(value_txt, (56, 142))

        if info:
            msg = font_small.render(info, True, (255, 120, 120))
            screen.blit(msg, (40, 195))

        pygame.display.flip()
        clock.tick(60)

# ============================================================
# 8) APPLICATION (Pygame + A* pondéré + UI)
# ============================================================

class AppliAStar:
    """
    Application Pygame affichant :
    - labyrinthe
    - exploration A* pondéré (auto ou pas à pas)
    - pingouin se déplaçant vers le noeud courant (animation)
    - possibilité de jouer le chemin trouvé

    Responsabilités :
    - gérer les états (mode, A*, overlays, brouillard)
    - rendu complet (UI + monde)
    - gestion du clavier (E, ESPACE, P, R, F, Q)
    """

    def __init__(self, grille, w):
        """
        Initialise la fenêtre, prépare le monde et l'UI, puis calcule un chemin
        “solution” via Weighted A* (offline) pour la touche P / affichage du coût.

        Args:
            grille (list[str]): labyrinthe.
            w (float): poids heuristique.

        Raises:
            ValueError: si 'S' ou 'E' sont absents.
        """
        pygame.init()
        pygame.display.set_caption(f"Labyrinthe - A* pondéré (w={w})")

        self.w = float(w)
        self.grille = grille
        self.lignes = hauteur(grille)
        self.colonnes = largeur(grille)

        self.depart = trouver_case(grille, "S")
        self.sortie = trouver_case(grille, "E")
        if self.depart is None or self.sortie is None:
            raise ValueError("Le labyrinthe doit contenir S et E")

        # ------------------------------------------------------------
        # COÛTS PAR CASE (stables via seed) -> coût d'entrée [1..4]
        # ------------------------------------------------------------
        """
        On attribue un coût d'entrée à chaque case traversable :
        - S et E coût=1 (cohérence)
        - autres cases coût aléatoire [1..4]
        - seed fixe -> même carte de coûts à chaque exécution (pédagogique)
        """
        self.couts = {}
        rng = random.Random(42)
        for r in range(self.lignes):
            for c in range(self.colonnes):
                if est_traversable(grille, r, c):
                    pos = (r, c)
                    ch = grille[r][c]
                    if ch in ("S", "E"):
                        self.couts[pos] = 1
                    else:
                        self.couts[pos] = rng.randint(1, 4)

        # Dimensions monde & fenêtre (monde + panneau droit + barres haut/bas)
        self.largeur_monde = self.colonnes * TAILLE_CASE
        self.hauteur_monde = self.lignes * TAILLE_CASE

        self.largeur_fenetre = self.largeur_monde + PANNEAU_DROIT_W
        self.hauteur_fenetre = HAUT_BAR_H + self.hauteur_monde + BAS_BAR_H

        self.ecran = pygame.display.set_mode((self.largeur_fenetre, self.hauteur_fenetre))
        self.clock = pygame.time.Clock()

        self.font_petit = pygame.font.SysFont("consolas", 15)
        self.font_tiny = pygame.font.SysFont("consolas", 13)

        # Pingouin : frames + état animation
        self.frames_pingouin = creer_frames_pingouin(int(TAILLE_CASE * 0.92))
        self.dir_pingouin = 2
        self.frame_pingouin = 0
        self.dernier_pas_anim = 0

        # Tuiles sol (alternance) + cache fog
        self.tuile_sol = [
            creer_tuile_bruitee(TAILLE_CASE, COL_SOL_1, COL_SOL_2, force=16, seed=1),
            creer_tuile_bruitee(TAILLE_CASE, COL_SOL_2, COL_SOL_1, force=16, seed=2),
        ]
        self._fog_tile_cache = {}

        # Solution calculée au reset (Weighted A* => pas toujours optimal si w>1)
        self.parent_solution = {}
        self.g_solution = {}

        self.reinitialiser_tout()

    # ============================================================
    # 8.1) RESET / INIT ÉTATS
    # ============================================================

    def reinitialiser_tout(self):
        """
        Remet l'application dans son état initial :
        - stoppe modes auto/step/play
        - efface overlays et compteurs
        - recalcule une solution “offline” avec Weighted A* (pour P + coût affiché)

        Returns:
            None
        """
        self.mode = "idle"  # idle | auto | step | play
        self.dernier_event_auto = 0

        self.etat_algo = None

        # Chemin trouvé (offline) + coût associé
        self.chemin_opt = None
        self.cout_opt = None

        # États visibles de l'algorithme (UI)
        self.visite = set()
        self.frontiere = set()
        self.courant = None
        self.parent = {}
        self.g = {}

        # Numérotation = ordre réel de passage du pingouin
        self.ordre = {self.depart: 1}
        self.prochain_num_ordre = 2

        # "vu" = cases révélées (visite/frontière/courant + pingouin)
        self.vu = {self.depart}

        # Texte haut : "vient de / peut aller"
        self.texte_haut = "Vient de: départ | Peut aller: —"

        # Position pingouin + direction
        self.pos_pingouin = self.depart
        self._set_dir_pingouin(self.depart, self.depart)

        # Stats de déplacement “physique”
        self.nb_pas = 0
        self.cout_total = 0

        # Route pingouin pour rejoindre noeud courant (animation)
        self.route = []
        self.index_route = 0
        self.afficher_violet = False
        self.dernier_pas_route = 0

        # Overlays
        self.overlay_chemin_opt = set()
        self.overlay_rebrousse = set()

        # Historique panneau droit
        self.histo = deque(maxlen=LIGNES_HISTO)

        # Animation chemin solution (P)
        self.index_chemin_opt = 0
        self.dernier_pas_opt = 0

        # Brouillard
        self.reveler_complet = False
        self.brouillard_actif = True

        # Calcul “offline” de la solution
        self._calculer_solution_astar_pondere()

    def reinitialiser_pour_chemin_optimal(self):
        """
        Prépare l'animation “play” sur le chemin solution (touche P) :
        - remet le pingouin au départ
        - active l'overlay du chemin
        - remet compteurs + historique

        Returns:
            None
        """
        self.mode = "play"
        self.pos_pingouin = self.depart
        self._set_dir_pingouin(self.depart, self.depart)

        self.nb_pas = 0
        self.cout_total = 0

        self.route = []
        self.index_route = 0
        self.afficher_violet = False
        self.overlay_rebrousse.clear()

        self.overlay_chemin_opt = set(self.chemin_opt) if self.chemin_opt else set()
        self.index_chemin_opt = 0
        self.dernier_pas_opt = 0

        self.ordre = {self.depart: 1}
        self.prochain_num_ordre = 2

        self._maj_texte_haut_depuis_position(self.pos_pingouin, "départ")
        self.histo.clear()

        self.reveler_complet = False
        self.brouillard_actif = True

    def _calculer_solution_astar_pondere(self):
        """
        Calcule une solution Weighted A* complète (offline) pour :
        - afficher le coût trouvé (barre basse)
        - permettre la touche P (jouer le chemin) sans lancer l'algo pas à pas

        IMPORTANT :
        - si w > 1, ce chemin n'est pas garanti optimal en coût.

        Effets de bord :
        - remplit parent_solution / g_solution
        - remplit chemin_opt / cout_opt

        Returns:
            None
        """
        etat = astar_initialiser(self.depart, self.sortie, self.w)
        while not etat["termine"]:
            astar_faire_une_etape(self.grille, etat, self.sortie, self.couts)

        if etat["trouve"]:
            self.parent_solution = dict(etat["parent"])
            self.g_solution = dict(etat["g"])
            self.chemin_opt = reconstruire_chemin(self.parent_solution, self.depart, self.sortie)
            self.cout_opt = self.g_solution.get(self.sortie, None)
        else:
            self.parent_solution = {}
            self.g_solution = {}
            self.chemin_opt = None
            self.cout_opt = None

    # ============================================================
    # 8.2) SYNC A* -> UI
    # ============================================================

    def _sync_depuis_etat_algo(self):
        """
        Synchronise les attributs UI depuis self.etat_algo :
        - visite/frontiere/courant/parent/g
        - met à jour self.vu (fog)
        - met à jour la barre haute + historique
        - planifie la route du pingouin vers le noeud courant
        - révèle tout si terminé + trouvé

        Returns:
            None
        """
        if self.etat_algo is None:
            return

        self.courant = self.etat_algo.get("courant", None)
        self.visite = set(self.etat_algo.get("visite", set()))
        self.frontiere = set(self.etat_algo.get("frontiere", set()))
        self.parent = dict(self.etat_algo.get("parent", {}))
        self.g = dict(self.etat_algo.get("g", {}))

        # cases "connues" (pour brouillard)
        if self.courant is not None:
            self.vu = set(self.visite) | set(self.frontiere) | {self.courant}
        else:
            self.vu = set(self.visite) | set(self.frontiere)

        # mise à jour barre haute + historique
        if self.courant is not None:
            par = self.parent.get(self.courant)
            if par is None:
                self._maj_texte_haut_depuis_position(self.courant, "départ")
            else:
                d = nom_direction(par, self.courant)
                self._maj_texte_haut_depuis_position(self.courant, (d.lower() if d else "—"))
            self._histo_push(self.texte_haut)

        # planifie l'animation du pingouin vers le noeud courant
        self._planifier_route_vers_courant()

        # fin algo -> révélation complète (brouillard)
        if self.etat_algo.get("termine") and self.etat_algo.get("trouve"):
            self.reveler_complet = True

    # ============================================================
    # 8.3) UI (texte, historique, direction, panneaux)
    # ============================================================

    def _dessiner_texte(self, x, y, txt, font, col=COL_TEXTE):
        """
        Dessine un texte avec ombre portée pour lisibilité.

        Args:
            x (int): position x (px)
            y (int): position y (px)
            txt (str): texte
            font (pygame.font.Font): police
            col (tuple[int,int,int]): couleur

        Returns:
            None
        """
        s = font.render(txt, True, col)
        sh = font.render(txt, True, COL_OMBRE)
        self.ecran.blit(sh, (x + 2, y + 2))
        self.ecran.blit(s, (x, y))

    def _histo_push(self, txt):
        """
        Ajoute une ligne dans l'historique (deque bornée LIGNES_HISTO).
        Tronque si la ligne est trop longue.

        Args:
            txt (str): texte à ajouter

        Returns:
            None
        """
        if len(txt) > 42:
            txt = txt[:41] + "…"
        self.histo.appendleft(txt)

    def _set_dir_pingouin(self, a, b):
        """
        Met à jour l'orientation du pingouin selon le déplacement a -> b.

        Args:
            a (tuple[int,int]): ancienne position
            b (tuple[int,int]): nouvelle position

        Returns:
            None
        """
        d = nom_direction(a, b)
        if d == "Haut": self.dir_pingouin = 0
        elif d == "Droite": self.dir_pingouin = 1
        elif d == "Bas": self.dir_pingouin = 2
        elif d == "Gauche": self.dir_pingouin = 3

    def _maj_texte_haut_depuis_position(self, pos, vient_de=None):
        """
        Met à jour la barre d'état haute :
        - “Vient de: ...”
        - “Peut aller: ...” (voisins traversables, sauf direction d'où l'on vient)

        Args:
            pos (tuple[int,int]): position de référence.
            vient_de (str | None): direction d'où l'on vient ("gauche", "droite", etc.) ou "départ".

        Returns:
            None
        """
        r, c = pos
        dirs = [nom for (_, _, nom) in voisins_4(self.grille, r, c)]
        if vient_de and vient_de != "départ":
            dirs = [d for d in dirs if d.lower() != vient_de.lower()]
        peut = ", ".join([d.lower() for d in dirs]) if dirs else "—"
        vient = vient_de if vient_de else "départ"
        self.texte_haut = f"Vient de: {vient} | Peut aller: {peut}"

    def _statut_deplacements(self):
        """
        Statut (depuis self.courant) pour chaque direction :
        - Bloqué (pas de voisin)
        - Déjà exploré (closed)
        - À explorer (open)
        - Nouveau

        Returns:
            dict[str,str]: mapping direction -> statut.
        """
        if self.courant is None:
            return {d: "—" for d in ["Haut", "Bas", "Gauche", "Droite"]}

        r, c = self.courant
        voisins = list(voisins_4(self.grille, r, c))
        possible = {d: None for d in ["Haut", "Bas", "Gauche", "Droite"]}
        for rr, cc, nom in voisins:
            possible[nom] = (rr, cc)

        out = {}
        for d in ["Haut", "Bas", "Gauche", "Droite"]:
            p = possible[d]
            if p is None:
                out[d] = "Bloqué"
            elif p in self.visite:
                out[d] = "Déjà exploré"
            elif p in self.frontiere:
                out[d] = "À explorer"
            else:
                out[d] = "Nouveau"
        return out

    def _info_pas_suivant_pingouin(self):
        """
        Construit les infos g/h/f affichées sur le panneau droit.

        - Pour la position du pingouin : g, h, f_w
        - Pour chaque direction : g/h/f estimés (ou connus si g déjà calculé)

        Remarque pédagogique :
        - Si g(voisin) n'est pas encore connu, on affiche g estimé =
          g(pingouin) + coût(voisin) (estimation locale).

        Returns:
            dict[str,str]: infos formatées (pingouin + directions)
        """
        pr, pc = self.pos_pingouin
        voisins = list(voisins_4(self.grille, pr, pc))
        possible = {d: None for d in ["Haut", "Bas", "Gauche", "Droite"]}
        for rr, cc, nom in voisins:
            possible[nom] = (rr, cc)

        g_base = self.g.get(self.pos_pingouin, None)

        out = {}
        if g_base is None:
            out["pingouin"] = f"Pingouin: g=— h=—  (w={self.w})"
        else:
            h0 = heuristique_manhattan(self.pos_pingouin, self.sortie)
            fw0 = g_base + self.w * h0
            out["pingouin"] = f"Pingouin: g={int(g_base)} h={int(h0)} f={int(fw0)}  (w={self.w})"

        for d in ["Haut", "Bas", "Gauche", "Droite"]:
            p = possible[d]
            if p is None:
                out[d] = "Bloqué"
                continue

            g_known = self.g.get(p, None)
            if g_known is not None:
                g2 = g_known
            elif g_base is not None:
                g2 = g_base + cout_case(self.couts, p)
            else:
                g2 = None

            h2 = heuristique_manhattan(p, self.sortie)

            if g2 is None:
                txt = f"g=— h={int(h2)} f=—"
            else:
                fw = g2 + self.w * h2
                txt = f"g={int(g2)} h={int(h2)} f={int(fw)}"

            out[d] = txt

        return out

    # ============================================================
    # 8.4) ROUTE pingouin vers noeud courant (rebroussement violet)
    # ============================================================

    def _planifier_route_vers_courant(self):
        """
        Planifie une route pingouin -> noeud courant (self.courant),
        en utilisant l'arbre parent.

        - route = full[1:] (on exclut la case actuelle)
        - si rebroussement (montée significative) :
            overlay violet = set(route)
            on efface au passage du pingouin

        Returns:
            None
        """
        if self.courant is None:
            self.route = []
            self.index_route = 0
            self.afficher_violet = False
            self.overlay_rebrousse.clear()
            return

        full, up_len = route_dans_arbre_parent_detail(self.parent, self.pos_pingouin, self.courant)
        route = full[1:]

        rebroussement = (up_len >= 2)

        self.route = route
        self.index_route = 0

        if rebroussement:
            self.overlay_rebrousse = set(route)
            self.afficher_violet = True
        else:
            self.overlay_rebrousse.clear()
            self.afficher_violet = False

    def _avancer_sur_route(self, now_ms):
        """
        Avance le pingouin d'un pas sur self.route (si timing OK).

        Met à jour :
        - nb_pas, cout_total
        - direction pingouin
        - cases vues (fog)
        - numéros de passage
        - effacement violet case par case
        - texte haut

        Args:
            now_ms (int): pygame.time.get_ticks()

        Returns:
            None
        """
        if self.index_route >= len(self.route):
            self.route = []
            self.afficher_violet = False
            return

        if now_ms - self.dernier_pas_route < PAS_ROUTE_MS:
            self._animer_pingouin(now_ms)
            return

        old = self.pos_pingouin
        nxt = self.route[self.index_route]
        self.index_route += 1

        if nxt != old:
            self.nb_pas += 1
            if nxt != self.depart:
                self.cout_total += cout_case(self.couts, nxt)

        self._set_dir_pingouin(old, nxt)
        self.pos_pingouin = nxt
        self.vu.add(nxt)

        if nxt not in self.ordre:
            self.ordre[nxt] = self.prochain_num_ordre
            self.prochain_num_ordre += 1

        if nxt in self.overlay_rebrousse:
            self.overlay_rebrousse.remove(nxt)

        d = nom_direction(old, nxt)
        vient_de = "départ"
        if d:
            vient_de = direction_opposee(d).lower()
        self._maj_texte_haut_depuis_position(self.pos_pingouin, vient_de)

        self.dernier_pas_route = now_ms
        self._animer_pingouin(now_ms)

    # ============================================================
    # 8.5) ANIMATION du chemin solution (touche P)
    # ============================================================

    def _maj_chemin_optimal(self, now_ms):
        """
        Anime le pingouin sur self.chemin_opt (mode play).

        - Respecte PAS_CHEMIN_MS
        - À la fin :
            mode idle
            push "Arrivé !!!"
            révélation complète (fog)

        Args:
            now_ms (int): temps courant (ms)

        Returns:
            None
        """
        if not self.chemin_opt:
            return

        if now_ms - self.dernier_pas_opt < PAS_CHEMIN_MS:
            self._animer_pingouin(now_ms)
            return

        if self.index_chemin_opt >= len(self.chemin_opt):
            self.mode = "idle"
            self._histo_push("Arrivé !!!")
            self.reveler_complet = True
            return

        old = self.pos_pingouin
        nxt = self.chemin_opt[self.index_chemin_opt]

        if nxt != old:
            self.nb_pas += 1
            if nxt != self.depart:
                self.cout_total += cout_case(self.couts, nxt)

        self._set_dir_pingouin(old, nxt)
        self.pos_pingouin = nxt
        self.vu.add(nxt)

        if nxt not in self.ordre:
            self.ordre[nxt] = self.prochain_num_ordre
            self.prochain_num_ordre += 1

        d = nom_direction(old, nxt)
        vient_de = "départ"
        if d:
            vient_de = direction_opposee(d).lower()
        self._maj_texte_haut_depuis_position(self.pos_pingouin, vient_de)

        self.index_chemin_opt += 1
        self.dernier_pas_opt = now_ms
        self._animer_pingouin(now_ms)

    # ============================================================
    # 8.6) ANIM pingouin
    # ============================================================

    def _animer_pingouin(self, now_ms):
        """
        Change la frame du pingouin selon ANIM_PINGOUIN_MS.

        Args:
            now_ms (int): temps courant (ms)

        Returns:
            None
        """
        if now_ms - self.dernier_pas_anim >= ANIM_PINGOUIN_MS:
            self.frame_pingouin = (self.frame_pingouin + 1) % 4
            self.dernier_pas_anim = now_ms

    # ============================================================
    # 8.7) DESSIN (monde, brouillard, UI)
    # ============================================================

    def _rect_case(self, r, c):
        """
        Convertit une coordonnée grille (r,c) en pygame.Rect écran.

        Args:
            r (int): ligne
            c (int): colonne

        Returns:
            pygame.Rect: rectangle pixel correspondant.
        """
        x = c * TAILLE_CASE
        y = HAUT_BAR_H + r * TAILLE_CASE
        return pygame.Rect(x, y, TAILLE_CASE, TAILLE_CASE)

    def dessiner_barre_haut(self):
        """
        Barre haute :
        - texte "vient de / peut aller"
        - info w + coût case + coût total

        Returns:
            None
        """
        pygame.draw.rect(self.ecran, COL_PANEL, pygame.Rect(0, 0, self.largeur_fenetre, HAUT_BAR_H))
        pygame.draw.line(self.ecran, COL_PANEL_BORD, (0, HAUT_BAR_H - 1), (self.largeur_fenetre, HAUT_BAR_H - 1), 2)

        cout_actuel = cout_case(self.couts, self.pos_pingouin)
        self._dessiner_texte(12, 7, self.texte_haut, self.font_petit)
        self._dessiner_texte(
            self.largeur_monde - 520, 7,
            f"w={self.w} | Coût case: {cout_actuel} | Coût total: {self.cout_total}",
            self.font_petit, COL_TEXTE_MUET
        )

    def dessiner_barre_bas(self):
        """
        Barre basse :
        - coût trouvé (chemin offline Weighted A*)
        - nb de pas réellement parcourus
        - rappel commandes

        Returns:
            None
        """
        y = HAUT_BAR_H + self.hauteur_monde
        pygame.draw.rect(self.ecran, COL_PANEL, pygame.Rect(0, y, self.largeur_fenetre, BAS_BAR_H))
        pygame.draw.line(self.ecran, COL_PANEL_BORD, (0, y), (self.largeur_fenetre, y), 2)

        opt = "—" if self.cout_opt is None else str(int(self.cout_opt))
        self._dessiner_texte(12, y + 8, f"Coût trouvé (A* pondéré) : {opt}", self.font_petit)
        self._dessiner_texte(12, y + 32, f"Pas parcourus : {self.nb_pas}", self.font_petit)

        self._dessiner_texte(self.largeur_fenetre - 520, y + 8, "Commandes :", self.font_petit, COL_TEXTE_MUET)
        self._dessiner_texte(
            self.largeur_fenetre - 920, y + 32,
            "E=Auto (A* pondéré)   ESPACE=Pas à Pas (A* pondéré)  P=Chemin trouvé   R=Reset   F=Brouillard on/off   Q=Quitter",
            self.font_petit
        )

    def dessiner_panneau_droit(self):
        """
        Panneau droit :
        - Historique (dernières actions)
        - Statut directions (bloqué/nouveau/open/closed)
        - Infos A* : g/h/f du pingouin + directions (pondéré avec w)

        Returns:
            None
        """
        x0 = self.largeur_monde
        y0 = HAUT_BAR_H
        h = self.hauteur_monde

        pygame.draw.rect(self.ecran, COL_PANEL, pygame.Rect(x0, y0, PANNEAU_DROIT_W, h))
        pygame.draw.rect(self.ecran, COL_PANEL_BORD, pygame.Rect(x0, y0, PANNEAU_DROIT_W, h), 2)

        self._dessiner_texte(x0 + 12, y0 + 10, "Historique", self.font_petit)
        for i, line in enumerate(list(self.histo)[:LIGNES_HISTO]):
            self._dessiner_texte(x0 + 12, y0 + 34 + i * 20, line, self.font_tiny)

        box_y = y0 + 34 + LIGNES_HISTO * 20 + 22
        self._dessiner_texte(x0 + 12, box_y, "Déplacements possibles", self.font_petit)
        box_y += 26

        st = self._statut_deplacements()
        for d in ["Haut", "Bas", "Gauche", "Droite"]:
            self._dessiner_texte(x0 + 12, box_y, f"{d:<7} → {st[d]}", self.font_tiny)
            box_y += 18

        box_y += 14
        self._dessiner_texte(x0 + 12, box_y, "Info A*", self.font_petit)
        box_y += 24

        info = self._info_pas_suivant_pingouin()
        self._dessiner_texte(x0 + 12, box_y, info["pingouin"], self.font_tiny, COL_TEXTE_MUET)
        box_y += 18
        for d in ["Haut", "Bas", "Gauche", "Droite"]:
            self._dessiner_texte(x0 + 12, box_y, f"{d:<7}: {info[d]}", self.font_tiny, COL_TEXTE_MUET)
            box_y += 18

    def _alpha_fog_spotlight(self, r, c):
        """
        Calcule l'alpha du brouillard pour la case (r,c) avec un effet “spotlight”.

        Règle :
        - base = ALPHA_FOG_CONNU si case déjà "vue", sinon ALPHA_FOG_INCONNU
        - proche du pingouin : alpha faible (plus visible)
        - loin : alpha -> base
        - transition adoucie (t^2)

        Args:
            r (int): ligne
            c (int): colonne

        Returns:
            int: alpha [0..255]
        """
        pr, pc = self.pos_pingouin
        d = math.sqrt((r - pr) ** 2 + (c - pc) ** 2)
        base = ALPHA_FOG_CONNU if (r, c) in self.vu else ALPHA_FOG_INCONNU

        if d <= RAYON_LUMIERE_CASES:
            return min(base, ALPHA_MIN_SPOT)
        if d >= RAYON_FONDU_CASES:
            return base

        t = (d - RAYON_LUMIERE_CASES) / (RAYON_FONDU_CASES - RAYON_LUMIERE_CASES)
        t = t * t
        a = int(ALPHA_MIN_SPOT * (1 - t) + base * t)
        return max(0, min(255, a))

    def _fog_tile(self, alpha):
        """
        Récupère (ou crée) une tuile de brouillard unie de taille TAILLE_CASE.

        Optimisation :
            Mise en cache par valeur d'alpha (int) pour limiter les allocations.

        Args:
            alpha (int|float): alpha demandé.

        Returns:
            pygame.Surface: tuile RGBA (noire) avec alpha.
        """
        a = int(alpha)
        if a not in self._fog_tile_cache:
            s = pygame.Surface((TAILLE_CASE, TAILLE_CASE), pygame.SRCALPHA)
            s.fill((0, 0, 0, a))
            self._fog_tile_cache[a] = s
        return self._fog_tile_cache[a]

    def dessiner_monde(self):
        """
        Dessine :
        - murs/sol
        - overlays (visited/frontier/current)
        - overlay chemin solution (vert)
        - overlay rebroussement (violet)
        - marqueurs S/E
        - numéros passage
        - coût d'entrée (haut-droite) et heuristique h (bas-droite)
        - brouillard (ne masque pas le violet)
        - pingouin

        Returns:
            None
        """
        for r in range(self.lignes):
            for c in range(self.colonnes):
                ch = self.grille[r][c]
                rect = self._rect_case(r, c)
                pos = (r, c)

                # ---- fond (mur vs sol) ----
                if ch == "#":
                    dessiner_rect_bevel(self.ecran, rect, COL_MUR, COL_MUR_HI, COL_MUR_SH, radius=7)
                else:
                    self.ecran.blit(self.tuile_sol[(r + c) % 2], rect.topleft)
                    dessiner_overlay_rgba(self.ecran, rect, (255, 255, 255, 18), radius=7)
                    pygame.draw.rect(self.ecran, COL_GRILLE, rect, 1)

                # ---- overlays A* ----
                if ch != "#":
                    if pos in self.visite:
                        dessiner_overlay_rgba(self.ecran, rect, COL_VISITE, radius=7, outline=(210, 245, 255, 120))
                    if pos in self.frontiere:
                        dessiner_overlay_rgba(self.ecran, rect, COL_A_EXPLORER, radius=7)
                    if self.courant == pos:
                        dessiner_overlay_rgba(self.ecran, rect, COL_COURANT, radius=7, outline=(235, 235, 245, 170))

                # ---- chemin solution (vert) ----
                if ch != "#" and pos in self.overlay_chemin_opt:
                    dessiner_overlay_rgba(self.ecran, rect, COL_CHEMIN_OPT, radius=7, outline=(235, 255, 245, 220))

                # ---- rebroussement (violet) ----
                if ch != "#" and pos in self.overlay_rebrousse:
                    dessiner_overlay_rgba(self.ecran, rect, COL_REBROUSSE, radius=7, outline=(255, 235, 255, 160))

                # ---- marqueurs S / E ----
                if ch == "S":
                    dessiner_glow(self.ecran, rect.center, COL_DEPART, r1=10, r2=26, alpha1=90)
                    pygame.draw.rect(self.ecran, COL_DEPART, rect.inflate(-12, -12), border_radius=10)
                elif ch == "E":
                    dessiner_glow(self.ecran, rect.center, COL_SORTIE, r1=10, r2=26, alpha1=90)
                    pygame.draw.rect(self.ecran, COL_SORTIE, rect.inflate(-12, -12), border_radius=10)

                # ---- numéro de passage (si déjà vu) ----
                if pos in self.vu and pos in self.ordre:
                    t = self.font_tiny.render(str(self.ordre[pos]), True, COL_NUM)
                    self.ecran.blit(t, (rect.x + 6, rect.y + 4))

                # ---- coût d'entrée + heuristique ----
                if ch != "#":
                    # coût d'entrée en rouge (haut-droite)
                    cost = self.couts.get(pos, 1)
                    ct = self.font_tiny.render(str(cost), True, COL_COUT)
                    self.ecran.blit(ct, (rect.right - ct.get_width() - 6, rect.y + 4))

                    # heuristique h en bas-droite (noir)
                    hval = 0 if pos == self.sortie else heuristique_manhattan(pos, self.sortie)
                    ht = self.font_tiny.render(str(hval), True, COL_H)
                    self.ecran.blit(ht, (rect.right - ht.get_width() - 6, rect.bottom - ht.get_height() - 4))

        # ---- brouillard (ne masque pas le violet) ----
        if self.brouillard_actif and not self.reveler_complet:
            for r in range(self.lignes):
                for c in range(self.colonnes):
                    pos = (r, c)
                    if pos in self.overlay_rebrousse:
                        continue
                    rect = self._rect_case(r, c)
                    alpha = self._alpha_fog_spotlight(r, c)
                    self.ecran.blit(self._fog_tile(alpha), rect.topleft)

        # ---- pingouin ----
        pr, pc = self.pos_pingouin
        rect = self._rect_case(pr, pc)
        frame = self.frames_pingouin[self.dir_pingouin][self.frame_pingouin]
        fw, fh = frame.get_size()
        self.ecran.blit(frame, (rect.x + (TAILLE_CASE - fw) // 2, rect.y + (TAILLE_CASE - fh) // 2))

    # ============================================================
    # 8.8) LOOP principal (clavier + MAJ + rendu)
    # ============================================================

    def run(self):
        """
        Boucle principale :
        - événements clavier
        - mise à jour A* (auto/step)
        - déplacement pingouin (vers courant ou chemin solution)
        - rendu complet + tick FPS

        Commandes :
        - Q : quitter
        - R : reset
        - F : brouillard on/off
        - E : mode auto (A* pondéré)
        - ESPACE : pas à pas (A* pondéré)
        - P : jouer le chemin trouvé (offline)
        """
        while True:
            now = pygame.time.get_ticks()

            # ---- événements ----
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_q:
                        pygame.quit()
                        sys.exit(0)

                    if ev.key == pygame.K_r:
                        self.reinitialiser_tout()

                    if ev.key == pygame.K_f:
                        self.brouillard_actif = not self.brouillard_actif

                    # E = auto (A* pondéré)
                    if ev.key == pygame.K_e:
                        self.reinitialiser_tout()
                        self.mode = "auto"
                        self.dernier_event_auto = 0
                        self.etat_algo = astar_initialiser(self.depart, self.sortie, self.w)
                        self._sync_depuis_etat_algo()

                    # ESPACE = pas à pas (A* pondéré)
                    if ev.key == pygame.K_SPACE:
                        # si on était en play ou qu'un overlay chemin était actif, reset avant step
                        if self.mode == "play" or self.overlay_chemin_opt:
                            self.reinitialiser_tout()

                        if self.etat_algo is None:
                            self.etat_algo = astar_initialiser(self.depart, self.sortie, self.w)

                        self.mode = "step"
                        astar_faire_une_etape(self.grille, self.etat_algo, self.sortie, self.couts)
                        self._sync_depuis_etat_algo()

                    # P = jouer le chemin calculé au reset
                    if ev.key == pygame.K_p:
                        self.reinitialiser_tout()
                        if self.chemin_opt:
                            self.reinitialiser_pour_chemin_optimal()
                        else:
                            self._histo_push("Pas de chemin trouvé.")

            # ---- déplacement pingouin vers le noeud courant (algo) ----
            if self.mode in ("auto", "step") and self.route:
                self._avancer_sur_route(now)

            # ---- auto: une étape seulement si la route est terminée ----
            if self.mode == "auto" and not self.route and self.etat_algo is not None:
                if now - self.dernier_event_auto >= ASTAR_EVENT_MS:
                    if self.etat_algo.get("termine"):
                        self.mode = "idle"
                        self.reveler_complet = True
                    else:
                        astar_faire_une_etape(self.grille, self.etat_algo, self.sortie, self.couts)
                        self._sync_depuis_etat_algo()
                        self.dernier_event_auto = now

            # ---- animation du chemin solution ----
            if self.mode == "play":
                self._maj_chemin_optimal(now)

            # ---- animation sprite ----
            self._animer_pingouin(now)

            # ---- rendu complet ----
            self.ecran.fill(COL_FOND)
            self.dessiner_barre_haut()
            self.dessiner_monde()
            self.dessiner_panneau_droit()
            self.dessiner_barre_bas()

            pygame.display.flip()
            self.clock.tick(FPS)

# ============================================================
# 9) POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    """
    Point d'entrée :
    1) petite fenêtre de saisie de w
    2) lancement de l'app principale

    Note :
        On quitte proprement via Q ou la croix de la fenêtre.
    """
    w = demander_w_pygame(default=1.8)
    AppliAStar(LABYRINTHE, w).run()
