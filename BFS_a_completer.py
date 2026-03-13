import sys
import random
import math
from collections import deque
import pygame

# ============================================================
# 0) IMPORTS & DÉPENDANCES
# ============================================================
"""
Imports :
- sys : fermeture propre (sys.exit) après pygame.quit()
- random : bruit / texture des tuiles
- math : sqrt pour le brouillard “spotlight”
- deque : file FIFO efficace pour BFS (O(1) popleft)
- pygame : rendu 2D, événements clavier, surfaces, fonts, timing

Bonnes pratiques :
- imports standard → imports externes
- éviter les imports inutilisés
"""

# ============================================================
# 1) PARAMÈTRES GÉNÉRAUX
# ============================================================
"""
Ce fichier contient une visualisation BFS (Breadth-First Search) sur un labyrinthe,
avec une interface Pygame (UI moderne + brouillard + animation d'un pingouin).

Objectifs pédagogiques :
- Montrer le fonctionnement du BFS étape par étape (file, visites, parents, distances).
- Visualiser la frontière, les visites, et le chemin optimal (si trouvé).
- Illustrer les “rebroussements” lors du déplacement du pingouin vers le nœud courant BFS.

Convention :
- (r, c) représente une case de grille : r = ligne, c = colonne
- Les temps sont en millisecondes (ms)
- Les positions pixel sont dérivées via TAILLE_CASE et offsets UI

Convention labyrinthe :
- '#' mur (non traversable)
- '.' sol traversable
- 'S' départ
- 'E' sortie

Hypothèse :
- toutes les lignes ont la même longueur

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
BFS_EVENT_MS = 260      # cadence des étapes BFS en auto
PAS_ROUTE_MS = 70       # déplacement pingouin vers la case courante
PAS_CHEMIN_MS = 90      # déplacement pingouin sur chemin optimal
ANIM_PINGOUIN_MS = 140  # cadence animation sprite pingouin

# UI
HAUT_BAR_H = 34
BAS_BAR_H = 64
PANNEAU_DROIT_W = 320
LIGNES_HISTO = 6

# ============================================================
# 2) THEME "MODERNE"
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

# Overlays BFS (RGBA)
COL_VISITE = (110, 220, 255, 150)
COL_A_EXPLORER = (255, 220, 120, 160)
COL_COURANT = (120, 175, 255, 190)

COL_CHEMIN_OPT = (160, 255, 190, 170)
COL_REBROUSSE = (210, 165, 255, 130)

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

# Numéros
COL_NUM_BFS = (235, 235, 240)  # ordre BFS (haut-gauche)

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
        L'ordre est CONTRACTUEL pour BFS (impacte l'ordre d'exploration) :
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
# 4) BFS EN DIRECT (LOGIQUE ISOLÉE)
# ============================================================

def bfs_initialiser(depart):
    """
    Initialise l'état nécessaire au BFS incrémental (étape par étape).

    TODO :
    - Créer une file (deque) contenant depart
    - Initialiser:
        visite (set) avec depart
        parent dict avec depart: None
        dist dict avec depart: 0
        ordre dict avec depart: 1
        prochain_id = 2
        courant = None
        termine = False
        trouve = False
    - Retourner un dict état avec ces clés:
        "file", "visite", "parent", "dist", "ordre", "prochain_id",
        "courant", "termine", "trouve"
    """
    # TODO: initialiser l'état BFS
    raise NotImplementedError("TODO: implémenter bfs_initialiser(depart)")


def bfs_faire_une_etape(grille, etat, arrivee):
    """
    Exécute UNE itération de BFS (pop file + push voisins).

    TODO :

    1) Si etat['termine'] est True : return

    2) Si la file est vide :
       - etat['termine'] = True
       - etat['trouve'] = False
       - etat['courant'] = None
       - return

    3) Sortir le prochain noeud à explorer (FIFO) :
       - courant = file.popleft()
       - etat['courant'] = courant

    4) Si courant == arrivee :
       - etat['termine'] = True
       - etat['trouve'] = True
       - return

    5) Parcourir les voisins (dans l’ordre de voisins_4 : Haut, Bas, Gauche, Droite)
       Pour chaque voisin nxt non visité :
       - ajouter nxt à visite
       - parent[nxt] = courant
       - dist[nxt] = dist[courant] + 1
       - ordre[nxt] = prochain_id ; prochain_id += 1
       - ajouter nxt à la file (append)

    Remarque :
    - BFS garantit le plus court chemin en nombre de pas (graphe non pondéré).
    """
    # TODO: implémenter une étape BFS
    raise NotImplementedError("TODO: implémenter bfs_faire_une_etape(grille, etat, arrivee)")


def bfs_reconstruire_chemin(parent, depart, arrivee):
    """
    Reconstruit un chemin depuis 'arrivee' en remontant via parent.

    TODO :
    - Si arrivee pas dans parent: return None
    - Remonter cur = arrivee jusqu'à None en ajoutant à une liste
    - Inverser la liste
    - Vérifier que chemin[0] == depart, sinon None
    - Retourner le chemin
    """
    # TODO: reconstruire le chemin via les parents
    raise NotImplementedError("TODO: implémenter bfs_reconstruire_chemin(parent, depart, arrivee)")


def bfs_cout_optimal(dist, arrivee):
    """
    Retourne le coût (distance BFS) de l'arrivée si connue.

    TODO :
    - Retourner dist[arrivee] si présent, sinon None
    """
    # TODO: retourner la distance optimale
    raise NotImplementedError("TODO: implémenter bfs_cout_optimal(dist, arrivee)")


# ============================================================
# 5) PINGOUIN (SPRITES DESSINÉS)
# ============================================================

def creer_frames_pingouin(taille):
    """
    Génère des sprites Pygame (surfaces) pour un pingouin animé.

    Structure:
        frames[direction][frame]
        - direction: 0=haut, 1=droite, 2=bas, 3=gauche
        - frame: 0..3 (petite variation pour simuler la marche)

    Notes:
        - Dessin vectoriel via primitives Pygame (ellipse, circle, polygon)
        - Les dimensions sont en pixels.

    Args:
        taille (int): taille d'une frame carrée (px).

    Returns:
        list[list[pygame.Surface]]: matrice 4x4 de surfaces avec canal alpha.
    """
    frames = [[None]*4 for _ in range(4)]
    for d in range(4):
        for i in range(4):
            surf = pygame.Surface((taille, taille), pygame.SRCALPHA)

            # Ombre portée au sol (ellipse semi-transparente)
            pygame.draw.ellipse(surf, (0, 0, 0, 70),
                                (int(taille*0.18), int(taille*0.82), int(taille*0.64), int(taille*0.16)))

            # Corps
            corps = pygame.Rect(int(taille*0.24), int(taille*0.22), int(taille*0.52), int(taille*0.62))
            pygame.draw.ellipse(surf, (25, 30, 40), corps)
            ventre = pygame.Rect(int(taille*0.30), int(taille*0.35), int(taille*0.40), int(taille*0.42))
            pygame.draw.ellipse(surf, (235, 235, 235), ventre)

            # Tête
            pygame.draw.circle(surf, (25, 30, 40), (int(taille*0.5), int(taille*0.26)), int(taille*0.20))

            # Yeux
            pygame.draw.circle(surf, (245, 245, 245), (int(taille*0.44), int(taille*0.24)), int(taille*0.04))
            pygame.draw.circle(surf, (245, 245, 245), (int(taille*0.56), int(taille*0.24)), int(taille*0.04))
            pygame.draw.circle(surf, (20, 20, 20), (int(taille*0.44), int(taille*0.24)), int(taille*0.02))
            pygame.draw.circle(surf, (20, 20, 20), (int(taille*0.56), int(taille*0.24)), int(taille*0.02))

            # Bec orienté selon la direction
            cx, cy = int(taille*0.5), int(taille*0.30)
            s = int(taille*0.08)
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
            pieds_y = int(taille*0.76)
            shift = 2 if (i % 2 == 0) else -2
            pygame.draw.ellipse(surf, (240, 180, 70),
                                (int(taille*0.34), pieds_y + shift, int(taille*0.14), int(taille*0.08)))
            pygame.draw.ellipse(surf, (240, 180, 70),
                                (int(taille*0.52), pieds_y - shift, int(taille*0.14), int(taille*0.08)))

            frames[d][i] = surf
    return frames

# ============================================================
# 6) ROUTE DANS L'ARBRE PARENT (pour LCA + rebroussement)
# ============================================================

def route_dans_arbre_parent_detail(parent, a, b):
    """
    Calcule un chemin de A vers B en utilisant uniquement l'arbre 'parent'.

    Objectif:
        Permettre au pingouin de “rejoindre” la case courante BFS via l'arbre
        (en remontant vers un ancêtre commun puis en redescendant).

    Concept:
        - On cherche le LCA (Lowest Common Ancestor) de a et b dans l'arbre parent.
        - full = chemin complet A -> ... -> LCA -> ... -> B
        - up_len = longueur de la portion “montée” A -> LCA (incluse)

    Args:
        parent (dict): mapping {node: parent_node} représentant un arbre enraciné.
        a (tuple[int,int]): point de départ dans l'arbre.
        b (tuple[int,int]): point d'arrivée dans l'arbre.

    Returns:
        tuple[list[tuple[int,int]], int]:
            - full: chemin A->B (liste de noeuds)
            - up_len: nb de noeuds dans la partie “montée” A->LCA incluse
              (donc full[:up_len] = montée; full[up_len-1:] = descente)

    Notes:
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
        c = rnd.randrange(-force, force+1)
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
    pygame.draw.line(surface, hi, (rect.left+radius, rect.top+1), (rect.right-radius, rect.top+1), 2)
    pygame.draw.line(surface, hi, (rect.left+1, rect.top+radius), (rect.left+1, rect.bottom-radius), 2)
    pygame.draw.line(surface, sh, (rect.left+radius, rect.bottom-2), (rect.right-radius, rect.bottom-2), 2)
    pygame.draw.line(surface, sh, (rect.right-2, rect.top+radius), (rect.right-2, rect.bottom-radius), 2)

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
        pygame.draw.rect(o, outline, pygame.Rect(1, 1, rect.w-2, rect.h-2), 2, border_radius=radius)
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
    for r in range(r2, r1-1, -3):
        t = 1.0 if r2 == r1 else (r - r1) / (r2 - r1)
        a = int(alpha1*(1-t) + alpha2*t)
        g = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(g, (*couleur_rgb, a), (r, r), r)
        ecran.blit(g, (centre[0]-r, centre[1]-r))

# ============================================================
# 8) APPLICATION
# ============================================================

class AppliBFS:
    """
    Application Pygame affichant :
    - une grille labyrinthe
    - l'exploration BFS (auto ou pas à pas)
    - un pingouin se déplaçant vers le “courant” BFS ou sur le chemin optimal

    Responsabilités principales :
    - Gestion des états (mode, BFS, overlays, brouillard)
    - Rendu (UI + monde)
    - Loop d'événements (clavier)
    """

    def __init__(self, grille):
        """
        Initialise Pygame, prépare les surfaces/typos/états, et calcule le chemin optimal.

        Args:
            grille (list[str]): labyrinthe (liste de chaînes).

        Raises:
            ValueError: si 'S' ou 'E' n'existent pas dans la grille.
        """
        pygame.init()
        pygame.display.set_caption("Mon labyrinthe en BFS")

        self.grille = grille
        self.lignes = hauteur(grille)
        self.colonnes = largeur(grille)

        self.depart = trouver_case(grille, "S")
        self.sortie = trouver_case(grille, "E")
        if self.depart is None or self.sortie is None:
            raise ValueError("Le labyrinthe doit contenir S et E")

        self.largeur_monde = self.colonnes * TAILLE_CASE
        self.hauteur_monde = self.lignes * TAILLE_CASE

        self.largeur_fenetre = self.largeur_monde + PANNEAU_DROIT_W
        self.hauteur_fenetre = HAUT_BAR_H + self.hauteur_monde + BAS_BAR_H

        self.ecran = pygame.display.set_mode((self.largeur_fenetre, self.hauteur_fenetre))
        self.clock = pygame.time.Clock()

        self.font_petit = pygame.font.SysFont("consolas", 15)
        self.font_tiny = pygame.font.SysFont("consolas", 13)

        self.frames_pingouin = creer_frames_pingouin(int(TAILLE_CASE * 0.92))
        self.dir_pingouin = 2
        self.frame_pingouin = 0
        self.dernier_pas_anim = 0

        # Deux tuiles alternées pour effet “sol”
        self.tuile_sol = [
            creer_tuile_bruitee(TAILLE_CASE, COL_SOL_1, COL_SOL_2, force=16, seed=1),
            creer_tuile_bruitee(TAILLE_CASE, COL_SOL_2, COL_SOL_1, force=16, seed=2),
        ]

        # Cache de tuiles de brouillard (évite de recréer une surface pour chaque alpha)
        self._fog_tile_cache = {}

        # Solution "globale" pour afficher le coût optimal dès le lancement
        self.parent_solution = {}
        self.dist_solution = {}

        self.reinitialiser_tout()

    # ------------------- RESET -------------------
    def reinitialiser_tout(self):
        """
        Remet l'application dans son état initial :
        - stoppe les modes auto/step/play
        - réinitialise les overlays, compteurs, historique
        - recalcule (si besoin) le chemin optimal global (pour affichage & touche P)

        Returns:
            None
        """
        self.mode = "idle"  # idle | auto | step | play
        self.dernier_event_auto = 0

        self.etat_bfs = None

        # Chemin optimal affiché en bas (calculé dès le lancement / après reset)
        self.chemin_opt = None
        self.cout_opt = None

        self.visite = set()
        self.frontiere = set()
        self.courant = None
        self.parent = {}
        self.dist = {}
        self.ordre = {self.depart: 1}
        self.vu = {self.depart}

        self.texte_haut = "Vient de: départ | Peut aller: —"

        self.pos_pingouin = self.depart
        self._set_dir_pingouin(self.depart, self.depart)
        self.nb_pas = 0
        self.compteur_pas_global = 0

        self.route = []
        self.index_route = 0
        self.numeros_route = []
        self.afficher_violet = False
        self.dernier_pas_route = 0

        self.overlay_chemin_opt = set()

        # Violet : chemin A->B quand rebroussement (effacé au passage)
        self.overlay_rebrousse = set()
        self._rebrousse_sequence = []

        self.histo = deque(maxlen=LIGNES_HISTO)

        self.index_chemin_opt = 0
        self.dernier_pas_opt = 0

        self.reveler_complet = False
        self.brouillard_actif = True

        # Calcul du chemin optimal dès le lancement / après reset
        self._calculer_solution_bfs_si_besoin()

    def reinitialiser_pour_chemin_optimal(self):
        """
        Prépare l'animation “play” sur le chemin optimal (touche P) :
        - remet le pingouin au départ
        - efface l'animation BFS pas à pas / auto
        - active l'overlay du chemin optimal

        Returns:
            None
        """
        self.mode = "play"
        self.pos_pingouin = self.depart
        self._set_dir_pingouin(self.depart, self.depart)
        self.nb_pas = 0
        self.compteur_pas_global = 0

        # On efface l'animation BFS en cours
        self.route = []
        self.index_route = 0
        self.numeros_route = []
        self.afficher_violet = False

        # On efface aussi le violet
        self.overlay_rebrousse.clear()
        self._rebrousse_sequence = []

        self.overlay_chemin_opt = set(self.chemin_opt) if self.chemin_opt else set()
        self.index_chemin_opt = 0
        self.dernier_pas_opt = 0

        self._maj_texte_haut_depuis_position(self.pos_pingouin, "départ")
        self.histo.clear()

        self.reveler_complet = False
        self.brouillard_actif = True

    # -------- Solution BFS au besoin (pour affichage coût + touche P) --------
    def _calculer_solution_bfs_si_besoin(self):
        """
        Calcule une solution BFS complète (offline) si elle n'est pas déjà disponible.

        Utilité:
            - Afficher dès le début “Chemin optimal : X pas”
            - Permettre la touche P (chemin optimal) même si l'utilisateur
              n'a pas lancé BFS pas-à-pas/auto.

        Effets de bord:
            Modifie:
                - self.parent_solution, self.dist_solution
                - self.chemin_opt, self.cout_opt

        Returns:
            None
        """
        if self.chemin_opt is not None and self.cout_opt is not None:
            return

        etat = bfs_initialiser(self.depart)
        while not etat["termine"]:
            bfs_faire_une_etape(self.grille, etat, self.sortie)

        if etat["trouve"]:
            self.parent_solution = dict(etat["parent"])
            self.dist_solution = dict(etat["dist"])
            self.chemin_opt = bfs_reconstruire_chemin(self.parent_solution, self.depart, self.sortie)
            self.cout_opt = bfs_cout_optimal(self.dist_solution, self.sortie)
        else:
            self.parent_solution = {}
            self.dist_solution = {}
            self.chemin_opt = None
            self.cout_opt = None

    # ------------------- SYNC BFS -> UI -------------------
    def _sync_depuis_etat_bfs(self):
        """
        Synchronise les attributs d'affichage (UI) depuis self.etat_bfs.

        Effets de bord:
            - Met à jour visite/frontiere/courant/parent/dist/ordre
            - Met à jour self.vu (cases visibles)
            - Ajoute une ligne dans l'historique
            - Planifie la route du pingouin vers le noeud courant
            - Si BFS terminé + trouvé => reconstruit chemin optimal + révèle tout

        Returns:
            None
        """
        if self.etat_bfs is None:
            return

        self.courant = self.etat_bfs.get("courant", None)
        self.visite = set(self.etat_bfs["visite"])
        self.frontiere = set(self.etat_bfs["file"])
        self.parent = dict(self.etat_bfs["parent"])
        self.dist = dict(self.etat_bfs["dist"])
        self.ordre = dict(self.etat_bfs["ordre"])

        if self.courant is not None:
            self.vu = set(self.visite) | set(self.frontiere) | {self.courant}
        else:
            self.vu = set(self.visite) | set(self.frontiere)

        if self.courant is not None:
            par = self.parent.get(self.courant)
            if par is None:
                self._maj_texte_haut_depuis_position(self.courant, "départ")
            else:
                d = nom_direction(par, self.courant)
                self._maj_texte_haut_depuis_position(self.courant, (d.lower() if d else "—"))
            self._histo_push(self.texte_haut)

        self._planifier_route_vers_courant()

        if self.etat_bfs.get("termine") and self.etat_bfs.get("trouve"):
            self.chemin_opt = bfs_reconstruire_chemin(self.parent, self.depart, self.sortie)
            self.cout_opt = bfs_cout_optimal(self.dist, self.sortie)
            self.reveler_complet = True

    # ------------------- UI -------------------
    def _dessiner_texte(self, x, y, txt, font, col=COL_TEXTE):
        """
        Dessine un texte avec ombre portée pour lisibilité.

        Args:
            x (int): x en pixels.
            y (int): y en pixels.
            txt (str): texte.
            font (pygame.font.Font): police.
            col (tuple[int,int,int]): couleur.

        Returns:
            None
        """
        s = font.render(txt, True, col)
        sh = font.render(txt, True, COL_OMBRE)
        self.ecran.blit(sh, (x+2, y+2))
        self.ecran.blit(s, (x, y))

    def _histo_push(self, txt):
        """
        Ajoute une ligne dans l'historique (file bornée LIGNES_HISTO).

        Note:
            Tronque si la ligne est trop longue (affichage compact).

        Args:
            txt (str): ligne.

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
            a (tuple[int,int]): ancienne position.
            b (tuple[int,int]): nouvelle position.

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
        Donne, pour la case courante BFS, le statut des 4 directions:
        - Bloqué (mur / hors-grille)
        - Déjà visité
        - À explorer (dans la file)
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
                out[d] = "Déjà visité"
            elif p in self.frontiere:
                out[d] = "À explorer"
            else:
                out[d] = "Nouveau"
        return out

    # ------------------- ROUTE -------------------
    def _planifier_route_vers_courant(self):
        """
        Calcule une route (liste de cases) pour déplacer le pingouin
        de sa position actuelle vers la case 'courant' (noeud BFS en cours).

        Détail:
            Utilise route_dans_arbre_parent_detail() pour autoriser
            rebroussement (remonter vers un ancêtre commun puis redescendre).

        Effets de bord:
            - self.route, self.index_route, self.numeros_route
            - self.overlay_rebrousse (violet) si rebroussement détecté

        Returns:
            None
        """
        if self.courant is None:
            self.route = []
            self.index_route = 0
            self.numeros_route = []
            self.afficher_violet = False
            self.overlay_rebrousse.clear()
            self._rebrousse_sequence = []
            return

        full, up_len = route_dans_arbre_parent_detail(self.parent, self.pos_pingouin, self.courant)
        route = full[1:]  # cases à parcourir (A exclu)

        # Rebroussement si la montée A->LCA fait au moins 1 pas
        rebroussement = (up_len >= 2)

        self.route = route
        self.index_route = 0
        self.numeros_route = [(pos, self.compteur_pas_global + i + 1) for i, pos in enumerate(self.route)]

        # Violet = CHEMIN COMPLET A->B (hors case actuelle), uniquement si rebroussement
        if rebroussement:
            self.overlay_rebrousse = set(route)
            self._rebrousse_sequence = route[:]
            self.afficher_violet = True
        else:
            self.overlay_rebrousse.clear()
            self._rebrousse_sequence = []
            self.afficher_violet = False

    def _avancer_sur_route(self, now_ms):
        """
        Fait avancer le pingouin d'un pas sur self.route (si timing OK).

        Règles:
            - Respecte PAS_ROUTE_MS (cadence)
            - Met à jour nb_pas et compteur_pas_global
            - Efface progressivement l'overlay violet au passage

        Args:
            now_ms (int): temps courant (pygame.time.get_ticks()).

        Returns:
            None
        """
        if self.index_route >= len(self.route):
            self.route = []
            self.numeros_route = []
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
            self.compteur_pas_global += 1

        self._set_dir_pingouin(old, nxt)
        self.pos_pingouin = nxt
        self.vu.add(nxt)

        # Effacement progressif du violet au passage du pingouin
        if nxt in self.overlay_rebrousse:
            self.overlay_rebrousse.remove(nxt)

        d = nom_direction(old, nxt)
        vient_de = "départ"
        if d:
            vient_de = direction_opposee(d).lower()
        self._maj_texte_haut_depuis_position(self.pos_pingouin, vient_de)

        self.dernier_pas_route = now_ms
        self._animer_pingouin(now_ms)

    # ------------------- CHEMIN OPT -------------------
    def _maj_chemin_optimal(self, now_ms):
        """
        Anime le pingouin sur le chemin optimal (mode 'play').

        Règles:
            - Respecte PAS_CHEMIN_MS
            - À la fin : mode idle + “Arrivé !!!” + révélation complète

        Args:
            now_ms (int): temps courant (ms).

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

        self._set_dir_pingouin(old, nxt)
        self.pos_pingouin = nxt
        self.vu.add(nxt)

        d = nom_direction(old, nxt)
        vient_de = "départ"
        if d:
            vient_de = direction_opposee(d).lower()
        self._maj_texte_haut_depuis_position(self.pos_pingouin, vient_de)

        self.index_chemin_opt += 1
        self.dernier_pas_opt = now_ms
        self._animer_pingouin(now_ms)

    # ------------------- ANIM -------------------
    def _animer_pingouin(self, now_ms):
        """
        Change la frame du pingouin selon ANIM_PINGOUIN_MS.

        Args:
            now_ms (int): temps courant (ms).

        Returns:
            None
        """
        if now_ms - self.dernier_pas_anim >= ANIM_PINGOUIN_MS:
            self.frame_pingouin = (self.frame_pingouin + 1) % 4
            self.dernier_pas_anim = now_ms

    # ------------------- DESSIN -------------------
    def _rect_case(self, r, c):
        """
        Convertit une coordonnée grille (r,c) en pygame.Rect écran.

        Args:
            r (int): ligne.
            c (int): colonne.

        Returns:
            pygame.Rect: rectangle pixel correspondant.
        """
        x = c * TAILLE_CASE
        y = HAUT_BAR_H + r * TAILLE_CASE
        return pygame.Rect(x, y, TAILLE_CASE, TAILLE_CASE)

    def dessiner_barre_haut(self):
        """
        Dessine la barre supérieure (texte d'état: “vient de / peut aller”).

        Returns:
            None
        """
        pygame.draw.rect(self.ecran, COL_PANEL, pygame.Rect(0, 0, self.largeur_fenetre, HAUT_BAR_H))
        pygame.draw.line(self.ecran, COL_PANEL_BORD, (0, HAUT_BAR_H-1), (self.largeur_fenetre, HAUT_BAR_H-1), 2)
        self._dessiner_texte(12, 7, self.texte_haut, self.font_petit)

    def dessiner_barre_bas(self):
        """
        Dessine la barre inférieure :
        - coût du chemin optimal
        - pas parcourus
        - rappel des commandes clavier

        Returns:
            None
        """
        y = HAUT_BAR_H + self.hauteur_monde
        pygame.draw.rect(self.ecran, COL_PANEL, pygame.Rect(0, y, self.largeur_fenetre, BAS_BAR_H))
        pygame.draw.line(self.ecran, COL_PANEL_BORD, (0, y), (self.largeur_fenetre, y), 2)

        opt = "—" if self.cout_opt is None else str(self.cout_opt)
        self._dessiner_texte(12, y + 8, f"Chemin optimal : {opt} pas", self.font_petit)
        self._dessiner_texte(12, y + 32, f"Pas parcourus : {self.nb_pas}", self.font_petit)

        self._dessiner_texte(self.largeur_fenetre - 520, y + 8, "Commandes :", self.font_petit, COL_TEXTE_MUET)
        self._dessiner_texte(
            self.largeur_fenetre - 820, y + 30,
            "E=BFS Auto   ESPACE=BFS Pas à Pas   P=Chemin Optimal   R=Reset   F=Brouillard on/off   Q=Quitter",
            self.font_petit
        )

    def dessiner_panneau_droit(self):
        """
        Dessine le panneau droit :
        - historique des actions
        - statut des déplacements possibles depuis la case BFS courante

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
            self._dessiner_texte(x0 + 12, y0 + 34 + i*20, line, self.font_tiny)

        box_y = y0 + 34 + LIGNES_HISTO*20 + 22
        self._dessiner_texte(x0 + 12, box_y, "Déplacements possibles", self.font_petit)
        box_y += 26

        st = self._statut_deplacements()
        for d in ["Haut", "Bas", "Gauche", "Droite"]:
            self._dessiner_texte(x0 + 12, box_y, f"{d:<7} → {st[d]}", self.font_tiny)
            box_y += 18

    def _alpha_fog_spotlight(self, r, c):
        """
        Calcule l'alpha du brouillard pour une case (r,c) avec un effet “spotlight”.

        Idée:
            - Plus on est proche du pingouin, plus on “voit clair”
            - Au-delà d'un rayon, on revient à l'alpha de base (connu vs inconnu)

        Args:
            r (int): ligne.
            c (int): colonne.

        Returns:
            int: alpha [0..255] à appliquer sur la case.
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

        Optimisation:
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
        Dessine la grille (murs/sol) + overlays BFS + chemin optimal + rebroussement + brouillard + pingouin.

        Note importante:
            Le brouillard NE doit PAS masquer le violet (rebroussement), sinon on perd l'information.

        Returns:
            None
        """
        for r in range(self.lignes):
            for c in range(self.colonnes):
                ch = self.grille[r][c]
                rect = self._rect_case(r, c)
                pos = (r, c)

                if ch == "#":
                    dessiner_rect_bevel(self.ecran, rect, COL_MUR, COL_MUR_HI, COL_MUR_SH, radius=7)
                else:
                    self.ecran.blit(self.tuile_sol[(r + c) % 2], rect.topleft)
                    dessiner_overlay_rgba(self.ecran, rect, (255, 255, 255, 18), radius=7)
                    pygame.draw.rect(self.ecran, COL_GRILLE, rect, 1)

                # Overlays BFS (visite/frontière/courant)
                if ch != "#":
                    if pos in self.visite:
                        dessiner_overlay_rgba(self.ecran, rect, COL_VISITE, radius=7, outline=(210, 245, 255, 120))
                    if pos in self.frontiere:
                        dessiner_overlay_rgba(self.ecran, rect, COL_A_EXPLORER, radius=7)
                    if self.courant == pos:
                        dessiner_overlay_rgba(self.ecran, rect, COL_COURANT, radius=7, outline=(235, 235, 245, 170))

                # Chemin optimal (vert)
                if ch != "#" and pos in self.overlay_chemin_opt:
                    dessiner_overlay_rgba(self.ecran, rect, COL_CHEMIN_OPT, radius=7, outline=(235, 255, 245, 220))

                # Rebroussement (violet)
                if ch != "#" and pos in self.overlay_rebrousse:
                    dessiner_overlay_rgba(self.ecran, rect, COL_REBROUSSE, radius=7, outline=(255, 235, 255, 160))

                # Marqueurs S / E
                if ch == "S":
                    dessiner_glow(self.ecran, rect.center, COL_DEPART, r1=10, r2=26, alpha1=90)
                    pygame.draw.rect(self.ecran, COL_DEPART, rect.inflate(-12, -12), border_radius=10)
                elif ch == "E":
                    dessiner_glow(self.ecran, rect.center, COL_SORTIE, r1=10, r2=26, alpha1=90)
                    pygame.draw.rect(self.ecran, COL_SORTIE, rect.inflate(-12, -12), border_radius=10)

                # Numéro BFS (ordre de découverte) uniquement si visible (vu)
                if pos in self.vu and pos in self.ordre:
                    t = self.font_tiny.render(str(self.ordre[pos]), True, COL_NUM_BFS)
                    self.ecran.blit(t, (rect.x + 6, rect.y + 4))

        # Brouillard (ne masque pas le violet)
        if self.brouillard_actif and not self.reveler_complet:
            for r in range(self.lignes):
                for c in range(self.colonnes):
                    pos = (r, c)
                    if pos in self.overlay_rebrousse:
                        continue  # laisse visible le violet

                    rect = self._rect_case(r, c)
                    alpha = self._alpha_fog_spotlight(r, c)
                    self.ecran.blit(self._fog_tile(alpha), rect.topleft)

        # Dessin du pingouin
        pr, pc = self.pos_pingouin
        rect = self._rect_case(pr, pc)
        frame = self.frames_pingouin[self.dir_pingouin][self.frame_pingouin]
        fw, fh = frame.get_size()
        self.ecran.blit(frame, (rect.x + (TAILLE_CASE - fw)//2, rect.y + (TAILLE_CASE - fh)//2))

    # ------------------- LOOP -------------------
    def run(self):
        """
        Boucle principale :
        - Gestion événements clavier
        - Mise à jour animations / BFS / déplacement pingouin
        - Rendu complet
        - Tick FPS

        Commandes:
            Q: quitter
            R: reset
            F: brouillard on/off
            E: BFS auto (reinit fort)
            ESPACE: BFS step-by-step
            P: animation chemin optimal

        Returns:
            None
        """
        while True:
            now = pygame.time.get_ticks()

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

                    # E = BFS auto (reset fort)
                    if ev.key == pygame.K_e:
                        self.reinitialiser_tout()
                        self.mode = "auto"
                        self.dernier_event_auto = 0
                        self.etat_bfs = bfs_initialiser(self.depart)
                        self._sync_depuis_etat_bfs()

                    # ESPACE = BFS pas à pas (reset si on vient de P)
                    if ev.key == pygame.K_SPACE:
                        if self.mode == "play" or self.overlay_chemin_opt:
                            self.reinitialiser_tout()

                        if self.etat_bfs is None:
                            self.etat_bfs = bfs_initialiser(self.depart)

                        self.mode = "step"
                        bfs_faire_une_etape(self.grille, self.etat_bfs, self.sortie)
                        self._sync_depuis_etat_bfs()

                    # P = chemin optimal (marche même si BFS pas encore lancé)
                    if ev.key == pygame.K_p:
                        self.reinitialiser_tout()
                        self._calculer_solution_bfs_si_besoin()
                        if self.chemin_opt:
                            self.reinitialiser_pour_chemin_optimal()
                        else:
                            self._histo_push("Pas de chemin trouvé.")

            # Déplacement pingouin sur route BFS
            if self.mode in ("auto", "step") and self.route:
                self._avancer_sur_route(now)

            # Auto BFS : une étape seulement si la route est terminée
            if self.mode == "auto" and not self.route and self.etat_bfs is not None:
                if now - self.dernier_event_auto >= BFS_EVENT_MS:
                    if self.etat_bfs.get("termine"):
                        self.mode = "idle"
                        self.reveler_complet = True
                    else:
                        bfs_faire_une_etape(self.grille, self.etat_bfs, self.sortie)
                        self._sync_depuis_etat_bfs()
                        self.dernier_event_auto = now

            # Chemin optimal
            if self.mode == "play":
                self._maj_chemin_optimal(now)

            self._animer_pingouin(now)

            self.ecran.fill(COL_FOND)
            self.dessiner_barre_haut()
            self.dessiner_monde()
            self.dessiner_panneau_droit()
            self.dessiner_barre_bas()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    """
    Point d'entrée du script.
    Lance l'application Pygame.
    """
    AppliBFS(LABYRINTHE).run()
