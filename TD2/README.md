# TD02 - Stratégies d'exploration informées

## Question 1 : Quelle recherche semble trouver la solution le plus rapidement ?

La recherche **A* Gloutonne (Greedy Best-First)** semble trouver la solution le plus rapidement. Elle explore moins de cases que les autres car elle se dirige toujours vers la case qui parait la plus proche de la sortie. Elle fonce droit vers l'objectif sans se soucier du coût du chemin parcouru.

L'A* pondéré est aussi rapide car il se rapproche du comportement glouton.

L'A* standard est le plus lent des trois car il explore plus de cases pour garantir de trouver le chemin optimal.

## Question 2 : Quels sont les avantage et inconvénient de chaque recherches ?

### A* standard

**Avantages :**
- Il trouve toujour le chemin optimal (le moin cher)
- Il est fiable, il trouve toujour une solution si elle existe

**Inconvénients :**
- Il explore beaucoups de case donc c'est plus lent
- Il prend plus de memoire

### A* Glouton

**Avantages :**
- Tres rapide car il explore pas beaucoup de case
- Il va directment vers la sortie

**Inconvénients :**
- Le chemin trouvé est pas forcemment le meilleur
- Il peut se retrouver dans des cul-de-sac car il regarde que la distane vers la sortie

### A* Pondéré

**Avantages :**
- C'est un comprimis entre A* et le glouton
- On peut regler le poid w pour etre plus ou moin rapide

**Inconvénients :**
- Si w est trop grand le chemin est pas optimale
- Faut trouver la bonne valeur de w

## Question 3 : Proposez une recherche informée plus optimale dans le cas du labyrinthe

