import json
import math
import random

import psycopg
from psycopg.rows import dict_row
from logzero import logger

NB_COLONNES = 10
NB_LIGNES = 10
COLONNES = "ABCDEFGHIJ"

NAVIRES_A_PLACER = [
    "porte-avion",
    "croiseur",
    "contre-torpilleur",
    "contre-torpilleur",
    "torpilleur",
]

TAILLE_NAVIRES = {
    "porte-avion": 5,
    "croiseur": 4,
    "contre-torpilleur": 3,
    "torpilleur": 2,
}

CODE_CARTE = {
    1: "C_MISSILE",
    2: "C_REJOUE",
    3: "C_VIDE",
    4: "C_MPM",
    5: "C_LEURRE",
    6: "C_WILLY",
    7: "C_MEGA",
    8: "C_ETOILE",
    9: "C_PASSE",
    10: "C_OUPS",
}

CARDES_SANS_COORDONNEES = {9, 10}


def execute_select_query(connexion, query, params=None):
    """
    Methode generique pour executer une requete SELECT.
    """
    params = params or []
    with connexion.cursor(row_factory=dict_row) as cursor:
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except psycopg.Error as exc:
            logger.error(exc)
    return None


def execute_other_query(connexion, query, params=None):
    """
    Methode generique pour executer une requete INSERT, UPDATE, DELETE.
    """
    params = params or []
    with connexion.cursor() as cursor:
        try:
            cursor.execute(query, params)
            return cursor.rowcount
        except psycopg.Error as exc:
            logger.error(exc)
    return None


def default_game_state():
    return {
        "phase": "creation",
        "tour_courant": 0,
        "partie_initialisee": False,
        "carte_joueur": None,
        "carte_adversaire": None,
        "tirs_restants_joueur": 0,
        "verification_vide": None,
        "dernier_tir_joueur": None,
        "dernier_tir_adversaire": None,
        "ia_cibles": [],
        "leurres": [],
        "willys": [],
        "navires_forces_coules": [],
    }


def ensure_game_schema(connexion):
    """
    Ajoute les colonnes minimales necessaires au moteur de jeu si besoin.
    """
    commandes = [
        "ALTER TABLE partie ADD COLUMN IF NOT EXISTS etat_jeu TEXT",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_navires_coules INT DEFAULT 0",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_navires_touches INT DEFAULT 0",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_cases_a_explorer INT DEFAULT 100",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_navires_coules INT DEFAULT 0",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_navires_touches INT DEFAULT 0",
        "ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_cases_a_explorer INT DEFAULT 100",
    ]
    with connexion.cursor() as cur:
        for commande in commandes:
            cur.execute(commande)


def load_game_state(raw_state):
    """
    Charge et complete l'etat de jeu stocke en JSON.
    """
    etat = default_game_state()
    if raw_state:
        try:
            donnees = json.loads(raw_state)
            if isinstance(donnees, dict):
                etat.update(donnees)
        except json.JSONDecodeError:
            logger.warning("Etat de jeu JSON invalide, reinitialisation.")
    if etat.get("ia_cibles") is None:
        etat["ia_cibles"] = []
    if etat.get("leurres") is None:
        etat["leurres"] = []
    if etat.get("willys") is None:
        etat["willys"] = []
    if etat.get("navires_forces_coules") is None:
        etat["navires_forces_coules"] = []
    return etat


def save_game_state(connexion, id_partie, state):
    """
    Sauvegarde l'etat de jeu JSON dans la partie.
    """
    with connexion.cursor() as cur:
        cur.execute(
            "UPDATE partie SET etat_jeu = %s WHERE id_partie = %s",
            (json.dumps(state), id_partie),
        )


def coord_to_label(x, y):
    if not cell_in_grid(x, y):
        return ""
    return f"{COLONNES[x - 1]}{y}"


def parse_coordonnee(coordonnee):
    """
    Convertit une coordonnee du type A5 en couple (x, y).
    """
    if coordonnee is None:
        return None
    propre = coordonnee.strip().upper().replace(" ", "")
    if len(propre) < 2:
        return None
    colonne = propre[0]
    ligne = propre[1:]
    if colonne not in COLONNES or not ligne.isdigit():
        return None
    x = COLONNES.index(colonne) + 1
    y = int(ligne)
    if not cell_in_grid(x, y):
        return None
    return x, y


def cell_in_grid(x, y):
    return 1 <= x <= NB_COLONNES and 1 <= y <= NB_LIGNES


def cells_from_navire(navire):
    taille = TAILLE_NAVIRES[navire["type"]]
    resultat = []
    for decalage in range(taille):
        x = navire["x"] + decalage if navire["sens"] == "H" else navire["x"]
        y = navire["y"] if navire["sens"] == "H" else navire["y"] + decalage
        if cell_in_grid(x, y):
            resultat.append((x, y))
    return resultat


def attack_cells_from_code(code, x, y):
    if x is None or y is None or code in CARDES_SANS_COORDONNEES:
        return []
    if code in (1, 2, 3, 4, 5, 6):
        return [(x, y)]
    if code == 7:
        resultat = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx = x + dx
                ny = y + dy
                if cell_in_grid(nx, ny):
                    resultat.append((nx, ny))
        return resultat
    if code == 8:
        resultat = []
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx = x + dx
                ny = y + dy
                if cell_in_grid(nx, ny):
                    resultat.append((nx, ny))
        return resultat
    return [(x, y)]


def get_partie_infos(connexion, id_partie):
    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                p.*,
                jh.pseudo AS pseudo_humain,
                jv.pseudo AS pseudo_virtuel,
                v.niveau AS niveau_virtuel
            FROM partie p
            JOIN joueur jh ON jh.id_joueur = p.id_humain
            JOIN joueur jv ON jv.id_joueur = p.id_virtuel
            JOIN virtuel v ON v.id_joueur = p.id_virtuel
            WHERE p.id_partie = %s
            """,
            (id_partie,),
        )
        return cur.fetchone()


def build_legacy_game_state(connexion, id_partie, partie):
    """
    Construit un etat minimal pour les parties existantes sans JSON.
    """
    etat = default_game_state()
    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(num_tour), 0) FROM tour WHERE id_partie = %s", (id_partie,))
        etat["tour_courant"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flotille WHERE id_partie = %s", (id_partie,))
        etat["partie_initialisee"] = cur.fetchone()[0] >= 2
    if partie["id_gagnant"] is not None:
        etat["phase"] = "terminee"
    return etat


def load_partie_for_player(connexion, id_partie, id_joueur):
    """
    Charge la partie si elle appartient bien au joueur humain courant.
    """
    ensure_game_schema(connexion)
    partie = get_partie_infos(connexion, id_partie)
    if partie is None or partie["id_humain"] != int(id_joueur):
        return None, None
    ensure_partie_has_pioche(connexion, partie)
    etat = load_game_state(partie.get("etat_jeu"))
    if partie.get("etat_jeu") is None:
        etat = build_legacy_game_state(connexion, id_partie, partie)
        save_game_state(connexion, id_partie, etat)
        partie["etat_jeu"] = json.dumps(etat)
    return partie, etat


def get_navires_partie(connexion, id_partie):
    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                n.*,
                f.id_joueur
            FROM navire n
            JOIN flotille f ON f.id_flotille = n.id_flotille
            WHERE f.id_partie = %s
            ORDER BY n.id_navire
            """,
            (id_partie,),
        )
        return cur.fetchall()


def get_tirs_partie(connexion, id_partie):
    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                t.*,
                c.code AS code_carte_type,
                tc.nom AS nom_carte
            FROM tir t
            LEFT JOIN carte c ON c.id_carte = t.id_carte
            LEFT JOIN type_carte tc ON tc.code = c.code
            WHERE t.id_partie = %s
            ORDER BY t.num_tour, t.num_tir
            """,
            (id_partie,),
        )
        return cur.fetchall()


def get_player_opponent(partie, id_joueur):
    if int(id_joueur) == int(partie["id_humain"]):
        return partie["id_virtuel"]
    return partie["id_humain"]


def build_exploration_maps(partie, tirs):
    """
    Retourne les cellules explorees sur chaque grille.
    """
    players = [partie["id_humain"], partie["id_virtuel"]]
    explorees_sur_grille = {player_id: set() for player_id in players}
    explorees_par_joueur = {player_id: set() for player_id in players}

    for tir in tirs:
        code = tir["code_carte_type"]
        if code == 9:
            continue
        if tir["x"] is None or tir["y"] is None:
            continue
        cases = set(attack_cells_from_code(code, tir["x"], tir["y"]))
        tireur = tir["id_joueur"]
        if code == 10:
            cible = tireur
        else:
            cible = get_player_opponent(partie, tireur)
            explorees_par_joueur[tireur].update(cases)
        explorees_sur_grille[cible].update(cases)

    return explorees_sur_grille, explorees_par_joueur


def refresh_navires_states(connexion, partie, state):
    """
    Recalcule l'etat des navires a partir des positions actuelles et des tirs.
    """
    navires = get_navires_partie(connexion, partie["id_partie"])
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    explorees_sur_grille, _ = build_exploration_maps(partie, tirs)
    forced = set(state.get("navires_forces_coules", []))

    with connexion.cursor() as cur:
        for navire in navires:
            cellules = set(cells_from_navire(navire))
            touchees = cellules & explorees_sur_grille[navire["id_joueur"]]
            if navire["id_navire"] in forced:
                nouvel_etat = "coule"
            elif len(touchees) >= len(cellules):
                nouvel_etat = "coule"
            elif touchees:
                nouvel_etat = "touche"
            else:
                nouvel_etat = "intact"
            if navire["etat"] != nouvel_etat:
                cur.execute(
                    "UPDATE navire SET etat = %s WHERE id_navire = %s",
                    (nouvel_etat, navire["id_navire"]),
                )


def get_ships_with_status(connexion, partie, state):
    refresh_navires_states(connexion, partie, state)
    return get_navires_partie(connexion, partie["id_partie"])


def create_partie(connexion, id_humain, id_virtuel):
    """
    Cree une nouvelle partie complete avec sa pioche et son etat JSON.
    """
    ensure_game_schema(connexion)
    source_pioche = get_default_source_pioche(connexion)
    if source_pioche is None:
        raise ValueError("Aucune pioche modele n'est disponible dans la base.")
    id_pioche = create_partie_pioche(connexion, source_pioche)
    etat = default_game_state()

    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id_partie), 0) + 1 FROM partie")
        id_partie = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO partie (
                id_partie,
                etat,
                score_final,
                id_humain,
                id_virtuel,
                id_pioche,
                id_gagnant,
                etat_jeu
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (id_partie, "cree", None, id_humain, id_virtuel, id_pioche, None, json.dumps(etat)),
        )
        cur.execute(
            """
            INSERT INTO sequence_temporelle (date_debut, heure_debut, date_fin, heure_fin, id_partie)
            VALUES (
                CURRENT_DATE,
                CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER),
                NULL,
                NULL,
                %s
            )
            """,
            (id_partie,),
        )
    return id_partie


def create_partie_pioche(connexion, source_pioche):
    """
    Duplique une pioche modele pour une nouvelle partie.
    """
    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id_pioche), 0) + 1 FROM pioche")
        id_pioche = cur.fetchone()[0]
        cur.execute("SELECT nom_distrib FROM pioche WHERE id_pioche = %s", (source_pioche,))
        ligne = cur.fetchone()
        nom = ligne[0] if ligne else "Distribution partie"
        cur.execute(
            "INSERT INTO pioche (id_pioche, nom_distrib) VALUES (%s, %s)",
            (id_pioche, f"{nom} - partie {id_pioche}"),
        )
        cur.execute(
            """
            INSERT INTO a_pour_distribution (id_pioche, code, pourcentage)
            SELECT %s, code, pourcentage
            FROM a_pour_distribution
            WHERE id_pioche = %s
            """,
            (id_pioche, source_pioche),
        )
        cur.execute(
            "SELECT id_carte FROM appartient WHERE id_pioche = %s ORDER BY id_carte",
            (source_pioche,),
        )
        ids_cartes = [row[0] for row in cur.fetchall()]

    random.shuffle(ids_cartes)
    with connexion.cursor() as cur:
        for rang, id_carte in enumerate(ids_cartes, start=1):
            cur.execute(
                """
                INSERT INTO appartient (id_carte, rang, id_pioche, etat)
                VALUES (%s, %s, %s, %s)
                """,
                (id_carte, rang, id_pioche, "disponible"),
            )
    return id_pioche


def get_default_source_pioche(connexion):
    """
    Retourne une pioche modele contenant bien des cartes.
    """
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT p.id_pioche
            FROM pioche p
            WHERE EXISTS (
                SELECT 1
                FROM appartient a
                WHERE a.id_pioche = p.id_pioche
            )
            ORDER BY CASE WHEN p.id_pioche = 105 THEN 0 ELSE 1 END, p.id_pioche
            LIMIT 1
            """
        )
        ligne = cur.fetchone()
        return ligne[0] if ligne else None


def ensure_partie_has_pioche(connexion, partie):
    """
    Rattache une pioche valide a la partie si elle n'en a pas ou si elle est vide.
    """
    id_pioche = partie.get("id_pioche")

    if id_pioche is not None:
        with connexion.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM appartient WHERE id_pioche = %s",
                (id_pioche,),
            )
            nb_cartes = cur.fetchone()[0]
        if nb_cartes > 0:
            return id_pioche

    source_pioche = get_default_source_pioche(connexion)
    if source_pioche is None:
        return None

    nouvelle_pioche = create_partie_pioche(connexion, source_pioche)
    with connexion.cursor() as cur:
        cur.execute(
            "UPDATE partie SET id_pioche = %s WHERE id_partie = %s",
            (nouvelle_pioche, partie["id_partie"]),
        )
    partie["id_pioche"] = nouvelle_pioche
    return nouvelle_pioche


def reset_pioche(connexion, id_pioche):
    with connexion.cursor() as cur:
        cur.execute("SELECT id_carte FROM appartient WHERE id_pioche = %s ORDER BY id_carte", (id_pioche,))
        ids_cartes = [row[0] for row in cur.fetchall()]
        cur.execute("DELETE FROM appartient WHERE id_pioche = %s", (id_pioche,))

    random.shuffle(ids_cartes)
    with connexion.cursor() as cur:
        for rang, id_carte in enumerate(ids_cartes, start=1):
            cur.execute(
                """
                INSERT INTO appartient (id_carte, rang, id_pioche, etat)
                VALUES (%s, %s, %s, %s)
                """,
                (id_carte, rang, id_pioche, "disponible"),
            )


def draw_next_card(connexion, id_pioche):
    """
    Tire la prochaine carte disponible dans la pioche.
    """
    if id_pioche is None:
        return None

    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                a.id_carte,
                c.code,
                tc.nom,
                tc.description,
                tc.image
            FROM appartient a
            JOIN carte c ON c.id_carte = a.id_carte
            JOIN type_carte tc ON tc.code = c.code
            WHERE a.id_pioche = %s
              AND a.etat = 'disponible'
            ORDER BY a.rang
            LIMIT 1
            """,
            (id_pioche,),
        )
        carte = cur.fetchone()

    if carte is None:
        reset_pioche(connexion, id_pioche)
        with connexion.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.id_carte,
                    c.code,
                    tc.nom,
                    tc.description,
                    tc.image
                FROM appartient a
                JOIN carte c ON c.id_carte = a.id_carte
                JOIN type_carte tc ON tc.code = c.code
                WHERE a.id_pioche = %s
                  AND a.etat = 'disponible'
                ORDER BY a.rang
                LIMIT 1
                """,
                (id_pioche,),
            )
            carte = cur.fetchone()

    if carte is None:
        return None

    with connexion.cursor() as cur:
        cur.execute(
            "UPDATE appartient SET etat = 'utilisee' WHERE id_pioche = %s AND id_carte = %s",
            (id_pioche, carte["id_carte"]),
        )

    return serialize_card(carte)


def serialize_card(carte):
    if carte is None:
        return None
    return {
        "id_carte": carte["id_carte"],
        "code": carte["code"],
        "code_nom": CODE_CARTE.get(carte["code"], "C_INCONNUE"),
        "nom": carte["nom"],
        "description": carte["description"],
        "image": normalize_card_image_path(carte["image"]),
        "effet_message": "",
    }


def normalize_card_image_path(image_path):
    """
    Normalise le chemin d'image d'une carte pour l'affichage web.
    """
    if image_path is None or image_path == "":
        return None
    if image_path.startswith("/"):
        return image_path
    return f"/bataille_navale/static/img/{image_path}"


def get_flotille_id(connexion, id_partie, id_joueur):
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT id_flotille FROM flotille WHERE id_partie = %s AND id_joueur = %s",
            (id_partie, id_joueur),
        )
        ligne = cur.fetchone()
        return ligne[0] if ligne else None


def create_flotille(connexion, id_partie, id_joueur, pavillon):
    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id_flotille), 0) + 1 FROM flotille")
        id_flotille = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO flotille (id_flotille, pavillon, nb_navires, id_joueur, id_partie)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_flotille, pavillon, 5, id_joueur, id_partie),
        )
    return id_flotille


def next_navire_id(connexion):
    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id_navire), 0) + 1 FROM navire")
        return cur.fetchone()[0]


def can_place_shape(cells, occupied, blocked):
    return all(cell_in_grid(x, y) for x, y in cells) and not (set(cells) & occupied) and not (set(cells) & blocked)


def random_ship_positions(blocked=None):
    blocked = blocked or set()
    occupied = set()
    navires = []
    for type_navire in NAVIRES_A_PLACER:
        taille = TAILLE_NAVIRES[type_navire]
        place = False
        for _ in range(400):
            sens = random.choice(["H", "V"])
            x = random.randint(1, NB_COLONNES)
            y = random.randint(1, NB_LIGNES)
            cellules = []
            for decalage in range(taille):
                nx = x + decalage if sens == "H" else x
                ny = y if sens == "H" else y + decalage
                cellules.append((nx, ny))
            if can_place_shape(cellules, occupied, blocked):
                navires.append({"type": type_navire, "x": x, "y": y, "sens": sens})
                occupied.update(cellules)
                place = True
                break
        if not place:
            raise ValueError("Impossible de placer tous les navires.")
    return navires


def initialize_partie_if_needed(connexion, partie, state):
    """
    Cree les flottilles et place les navires une seule fois.
    """
    if state.get("partie_initialisee"):
        return

    with connexion.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM flotille WHERE id_partie = %s", (partie["id_partie"],))
        nb_flotilles = cur.fetchone()[0]

    if nb_flotilles >= 2:
        state["partie_initialisee"] = True
        return

    flotille_humain = create_flotille(connexion, partie["id_partie"], partie["id_humain"], "France")
    flotille_virtuel = create_flotille(connexion, partie["id_partie"], partie["id_virtuel"], "Virtuel")

    positions_humain = random_ship_positions()
    positions_virtuel = random_ship_positions()

    id_navire = next_navire_id(connexion)
    with connexion.cursor() as cur:
        for position in positions_humain:
            cur.execute(
                """
                INSERT INTO navire (id_navire, type, x, y, sens, etat, id_flotille)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (id_navire, position["type"], position["x"], position["y"], position["sens"], "intact", flotille_humain),
            )
            id_navire += 1
        for position in positions_virtuel:
            cur.execute(
                """
                INSERT INTO navire (id_navire, type, x, y, sens, etat, id_flotille)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (id_navire, position["type"], position["x"], position["y"], position["sens"], "intact", flotille_virtuel),
            )
            id_navire += 1

    state["partie_initialisee"] = True


def ensure_turn_exists(connexion, id_partie, num_tour):
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM tour WHERE id_partie = %s AND num_tour = %s",
            (id_partie, num_tour),
        )
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO tour (
                    num_tour,
                    id_partie,
                    joueur_navires_coules,
                    joueur_navires_touches,
                    joueur_cases_a_explorer,
                    adversaire_navires_coules,
                    adversaire_navires_touches,
                    adversaire_cases_a_explorer
                )
                VALUES (%s, %s, 0, 0, 100, 0, 0, 100)
                """,
                (num_tour, id_partie),
            )


def open_sequence_if_needed(connexion, id_partie):
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM sequence_temporelle
            WHERE id_partie = %s
              AND date_fin IS NULL
              AND heure_fin IS NULL
            """,
            (id_partie,),
        )
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO sequence_temporelle (date_debut, heure_debut, date_fin, heure_fin, id_partie)
                VALUES (
                    CURRENT_DATE,
                    CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER),
                    NULL,
                    NULL,
                    %s
                )
                """,
                (id_partie,),
            )


def close_open_sequence(connexion, id_partie):
    with connexion.cursor() as cur:
        cur.execute(
            """
            UPDATE sequence_temporelle
            SET
                date_fin = CURRENT_DATE,
                heure_fin = CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER)
            WHERE id_partie = %s
              AND date_fin IS NULL
              AND heure_fin IS NULL
            """,
            (id_partie,),
        )


def get_special_cells(state, id_joueur):
    leurres_actifs = []
    for leurre in state.get("leurres", []):
        if leurre["owner"] == id_joueur and leurre.get("actif"):
            leurres_actifs.extend([tuple(cell) for cell in leurre["cells"]])

    willys_actifs = []
    for willy in state.get("willys", []):
        if willy["owner"] == id_joueur and willy.get("actif"):
            willys_actifs.append((willy["x"], willy["y"]))
    return set(leurres_actifs), set(willys_actifs)


def get_player_ships(connexion, partie, state, id_joueur):
    navires = get_ships_with_status(connexion, partie, state)
    return [navire for navire in navires if navire["id_joueur"] == id_joueur]


def get_player_occupied_cells(connexion, partie, state, id_joueur, exclude_navire=None):
    occupied = set()
    for navire in get_player_ships(connexion, partie, state, id_joueur):
        if exclude_navire is not None and navire["id_navire"] == exclude_navire:
            continue
        occupied.update(cells_from_navire(navire))
    leurres, willys = get_special_cells(state, id_joueur)
    occupied.update(leurres)
    occupied.update(willys)
    return occupied


def random_shape_of_size(taille, occupied, blocked):
    for _ in range(400):
        sens = random.choice(["H", "V"])
        x = random.randint(1, NB_COLONNES)
        y = random.randint(1, NB_LIGNES)
        cellules = []
        for decalage in range(taille):
            nx = x + decalage if sens == "H" else x
            ny = y if sens == "H" else y + decalage
            cellules.append((nx, ny))
        if can_place_shape(cellules, occupied, blocked):
            return {"x": x, "y": y, "sens": sens, "cells": cellules}
    return None


def apply_meme_pas_mal(connexion, partie, state, id_joueur):
    """
    Deplace un navire touche vers une zone non exploree.
    """
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    explorees_sur_grille, _ = build_exploration_maps(partie, tirs)
    navires = get_player_ships(connexion, partie, state, id_joueur)
    navires_touches = [navire for navire in navires if navire["etat"] == "touche"]
    if not navires_touches:
        return "Aucun navire touche a deplacer."

    navire = navires_touches[0]
    taille = TAILLE_NAVIRES[navire["type"]]
    occupied = get_player_occupied_cells(connexion, partie, state, id_joueur, exclude_navire=navire["id_navire"])
    blocked = set(explorees_sur_grille[id_joueur])
    nouvelle_position = random_shape_of_size(taille, occupied, blocked)
    if nouvelle_position is None:
        return "Aucun emplacement libre n'a ete trouve pour Meme pas mal."

    with connexion.cursor() as cur:
        cur.execute(
            """
            UPDATE navire
            SET x = %s, y = %s, sens = %s, etat = 'intact'
            WHERE id_navire = %s
            """,
            (nouvelle_position["x"], nouvelle_position["y"], nouvelle_position["sens"], navire["id_navire"]),
        )
    return f"Le navire {navire['type']} a ete deplace vers {coord_to_label(nouvelle_position['x'], nouvelle_position['y'])}."


def place_leurre(connexion, partie, state, id_joueur):
    occupied = get_player_occupied_cells(connexion, partie, state, id_joueur)
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    explorees_sur_grille, _ = build_exploration_maps(partie, tirs)
    forme = random_shape_of_size(2, occupied, explorees_sur_grille[id_joueur])
    if forme is None:
        return "Impossible de placer un leurre pour ce tour."
    state["leurres"].append(
        {
            "owner": id_joueur,
            "cells": [[cell[0], cell[1]] for cell in forme["cells"]],
            "actif": True,
            "hit_cell": None,
            "touched_by": None,
        }
    )
    return f"Un bateau leurre a ete place a partir de {coord_to_label(forme['x'], forme['y'])}."


def place_willy(connexion, partie, state, id_joueur):
    occupied = get_player_occupied_cells(connexion, partie, state, id_joueur)
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    explorees_sur_grille, _ = build_exploration_maps(partie, tirs)
    blocked = occupied | set(explorees_sur_grille[id_joueur])
    candidats = [(x, y) for x in range(1, NB_COLONNES + 1) for y in range(1, NB_LIGNES + 1) if (x, y) not in blocked]
    if not candidats:
        return "Impossible de placer Willy pour ce tour."
    x, y = random.choice(candidats)
    state["willys"].append({"owner": id_joueur, "x": x, "y": y, "actif": True})
    return f"Willy nage maintenant en {coord_to_label(x, y)}."


def apply_card_start_bonus(connexion, partie, state, id_joueur, carte):
    code = carte["code"]
    messages = []
    tirs = 1

    if code == 2:
        tirs = 2
        messages.append("Cette carte vous donne deux tirs dans ce tour.")
    elif code == 4:
        messages.append(apply_meme_pas_mal(connexion, partie, state, id_joueur))
    elif code == 5:
        messages.append(place_leurre(connexion, partie, state, id_joueur))
    elif code == 6:
        messages.append(place_willy(connexion, partie, state, id_joueur))
    elif code == 9:
        messages.append("Cette carte vous fait passer votre tour.")
    elif code == 10:
        messages.append("Cette carte provoquera un tir accidentel sur votre propre flotte.")

    carte["effet_message"] = " ".join(message for message in messages if message)
    return tirs


def start_new_turn(connexion, partie, state):
    initialize_partie_if_needed(connexion, partie, state)
    open_sequence_if_needed(connexion, partie["id_partie"])
    with connexion.cursor() as cur:
        cur.execute("UPDATE partie SET etat = 'en cours' WHERE id_partie = %s", (partie["id_partie"],))

    state["tour_courant"] += 1
    ensure_turn_exists(connexion, partie["id_partie"], state["tour_courant"])
    state["verification_vide"] = None
    state["dernier_tir_joueur"] = None
    state["dernier_tir_adversaire"] = None
    state["carte_adversaire"] = None

    ensure_partie_has_pioche(connexion, partie)
    carte = draw_next_card(connexion, partie["id_pioche"])
    if carte is None:
        raise ValueError("Aucune carte n'est disponible dans la pioche de cette partie.")
    state["carte_joueur"] = carte
    state["tirs_restants_joueur"] = apply_card_start_bonus(connexion, partie, state, partie["id_humain"], carte)
    state["phase"] = "tir_joueur"

    refresh_navires_states(connexion, partie, state)
    update_current_tour_stats(connexion, partie, state)
    save_game_state(connexion, partie["id_partie"], state)


def get_next_num_tir(connexion, id_partie, num_tour):
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(num_tir), 0) + 1 FROM tir WHERE id_partie = %s AND num_tour = %s",
            (id_partie, num_tour),
        )
        return cur.fetchone()[0]


def get_card_by_id(connexion, id_carte):
    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT c.id_carte, c.code, tc.nom, tc.description, tc.image
            FROM carte c
            JOIN type_carte tc ON tc.code = c.code
            WHERE c.id_carte = %s
            """,
            (id_carte,),
        )
        return cur.fetchone()


def insert_tir(connexion, id_partie, num_tour, id_carte, id_joueur, x=None, y=None):
    num_tir = get_next_num_tir(connexion, id_partie, num_tour)
    with connexion.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tir (num_tir, num_tour, id_partie, id_carte, id_joueur, x, y)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (num_tir, num_tour, id_partie, id_carte, id_joueur, x, y),
        )


def get_ship_cell_owner_map(navires):
    resultat = {}
    for navire in navires:
        for cell in cells_from_navire(navire):
            resultat[cell] = navire
    return resultat


def choose_random_ship_cell(connexion, partie, state, id_joueur):
    navires = get_player_ships(connexion, partie, state, id_joueur)
    candidats = []
    for navire in navires:
        if navire["etat"] == "coule":
            continue
        candidats.extend(cells_from_navire(navire))
    if not candidats:
        return None
    return random.choice(candidats)


def sink_smallest_ships(connexion, partie, state, id_joueur, limit_count=3):
    navires = get_player_ships(connexion, partie, state, id_joueur)
    navires_restants = [navire for navire in navires if navire["etat"] != "coule"]
    navires_restants.sort(key=lambda navire: (TAILLE_NAVIRES[navire["type"]], navire["id_navire"]))
    cibles = navires_restants[:limit_count]
    forced = set(state.get("navires_forces_coules", []))
    for navire in cibles:
        forced.add(navire["id_navire"])
    state["navires_forces_coules"] = sorted(forced)
    return cibles


def treat_special_cell_hit(connexion, partie, state, tireur, cible, cell):
    """
    Gere les impacts sur leurre ou Willy.
    """
    x, y = cell
    for willy in state.get("willys", []):
        if willy["owner"] == cible and willy.get("actif") and willy["x"] == x and willy["y"] == y:
            willy["actif"] = False
            navires_coules = sink_smallest_ships(connexion, partie, state, tireur, 3)
            return {
                "resultat": "willy",
                "message": "Willy a ete touche.",
                "navires_coules_willy": [navire["type"] for navire in navires_coules],
            }

    for leurre in state.get("leurres", []):
        cells = [tuple(case) for case in leurre["cells"]]
        if leurre["owner"] == cible and leurre.get("actif") and cell in cells:
            leurre["actif"] = False
            leurre["hit_cell"] = [x, y]
            leurre["touched_by"] = tireur
            return {"resultat": "leurre", "message": "Un bateau leurre a ete touche."}

    return None


def execute_attack_action(connexion, partie, state, tireur, carte, coordonnee):
    """
    Execute un tir humain ou virtuel avec sa carte.
    """
    before_states = {navire["id_navire"]: navire["etat"] for navire in get_ships_with_status(connexion, partie, state)}
    cible = get_player_opponent(partie, tireur)
    code = carte["code"]
    resume = {
        "carte": carte,
        "coordonnee": None,
        "impacts": [],
        "message": "",
        "navires_coules": [],
        "partie_finie": False,
    }

    if code == 9:
        insert_tir(connexion, partie["id_partie"], state["tour_courant"], carte["id_carte"], tireur, None, None)
        resume["message"] = "Le joueur passe son tour."
        return resume

    if code == 10:
        cell = choose_random_ship_cell(connexion, partie, state, tireur)
        if cell is None:
            insert_tir(connexion, partie["id_partie"], state["tour_courant"], carte["id_carte"], tireur, None, None)
            resume["message"] = "Aucun navire n'etait disponible pour le tir accidentel."
            return resume
        x, y = cell
        insert_tir(connexion, partie["id_partie"], state["tour_courant"], carte["id_carte"], tireur, x, y)
        refresh_navires_states(connexion, partie, state)
        after_states = {navire["id_navire"]: navire["etat"] for navire in get_ships_with_status(connexion, partie, state)}
        resume["coordonnee"] = coord_to_label(x, y)
        resume["impacts"] = [{"coordonnee": coord_to_label(x, y), "resultat": "oups"}]
        resume["navires_coules"] = get_newly_sunk_ships(connexion, partie, state, tireur, before_states, after_states)
        resume["message"] = f"Le missile a frappe votre propre flotte en {coord_to_label(x, y)}."
        return resume

    x, y = coordonnee
    cellules = attack_cells_from_code(code, x, y)
    insert_tir(connexion, partie["id_partie"], state["tour_courant"], carte["id_carte"], tireur, x, y)
    navires = get_ships_with_status(connexion, partie, state)
    ship_map = get_ship_cell_owner_map(navires)

    for cellule in cellules:
        special = treat_special_cell_hit(connexion, partie, state, tireur, cible, cellule)
        if special is not None:
            impact = {"coordonnee": coord_to_label(cellule[0], cellule[1]), "resultat": special["resultat"]}
            if special.get("navires_coules_willy"):
                impact["navires_coules_willy"] = special["navires_coules_willy"]
            resume["impacts"].append(impact)
            continue

        navire = ship_map.get(cellule)
        if navire is not None and navire["id_joueur"] == cible:
            resume["impacts"].append({"coordonnee": coord_to_label(cellule[0], cellule[1]), "resultat": "touche"})
        else:
            resume["impacts"].append({"coordonnee": coord_to_label(cellule[0], cellule[1]), "resultat": "eau"})

    refresh_navires_states(connexion, partie, state)
    after_states = {navire["id_navire"]: navire["etat"] for navire in get_ships_with_status(connexion, partie, state)}
    resume["coordonnee"] = coord_to_label(x, y)
    resume["navires_coules"] = get_newly_sunk_ships(connexion, partie, state, cible, before_states, after_states)
    resume["message"] = build_attack_message(resume)
    return resume


def get_newly_sunk_ships(connexion, partie, state, id_joueur_cible, before_states, after_states):
    navires = get_player_ships(connexion, partie, state, id_joueur_cible)
    resultat = []
    for navire in navires:
        if before_states.get(navire["id_navire"]) != "coule" and after_states.get(navire["id_navire"]) == "coule":
            resultat.append(navire["type"])
    return resultat


def build_attack_message(resume):
    if not resume["impacts"]:
        return "Aucun impact."

    touches = [impact["coordonnee"] for impact in resume["impacts"] if impact["resultat"] in ("touche", "leurre", "willy")]
    eaux = [impact["coordonnee"] for impact in resume["impacts"] if impact["resultat"] == "eau"]

    morceaux = []
    if touches:
        morceaux.append("Touches en " + ", ".join(touches))
    if eaux:
        morceaux.append("A l'eau en " + ", ".join(eaux))
    if resume["navires_coules"]:
        morceaux.append("Navire(s) coule(s) : " + ", ".join(resume["navires_coules"]))
    return " - ".join(morceaux)


def get_attack_grid_explored(connexion, partie, id_joueur):
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    _, explorees_par_joueur = build_exploration_maps(partie, tirs)
    return set(explorees_par_joueur[id_joueur])


def choose_ai_target(connexion, partie, state, carte):
    id_ia = partie["id_virtuel"]
    navires_humain = get_player_ships(connexion, partie, state, partie["id_humain"])
    ship_cells = set()
    for navire in navires_humain:
        ship_cells.update(cells_from_navire(navire))

    explorees = get_attack_grid_explored(connexion, partie, id_ia)
    niveau = (partie["niveau_virtuel"] or "novice").lower()
    queue = [tuple(case) for case in state.get("ia_cibles", [])]
    queue = [case for case in queue if case not in explorees]
    state["ia_cibles"] = [[case[0], case[1]] for case in queue]

    if carte["code"] == 3:
        candidats = [case for case in ship_cells if case not in explorees]
        if candidats:
            return random.choice(candidats)

    if niveau in ("intermediaire", "expert") and queue:
        choix = queue[0]
        state["ia_cibles"] = [[case[0], case[1]] for case in queue[1:]]
        return choix

    candidats = [(x, y) for x in range(1, NB_COLONNES + 1) for y in range(1, NB_LIGNES + 1) if (x, y) not in explorees]
    if niveau in ("intermediaire", "expert"):
        damier = [case for case in candidats if (case[0] + case[1]) % 2 == 0]
        if damier:
            return random.choice(damier)
    return random.choice(candidats) if candidats else None


def update_ai_targets_with_resume(connexion, partie, state, resume):
    if resume["navires_coules"]:
        state["ia_cibles"] = []
        return
    explorees = get_attack_grid_explored(connexion, partie, partie["id_virtuel"])
    deja = {tuple(case) for case in state.get("ia_cibles", [])}
    for impact in resume["impacts"]:
        if impact["resultat"] != "touche":
            continue
        coord = parse_coordonnee(impact["coordonnee"])
        if coord is None:
            continue
        x, y = coord
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = x + dx
            ny = y + dy
            cellule = (nx, ny)
            if cell_in_grid(nx, ny) and cellule not in explorees and cellule not in deja:
                state["ia_cibles"].append([nx, ny])
                deja.add(cellule)


def execute_ai_turn(connexion, partie, state):
    carte = draw_next_card(connexion, partie["id_pioche"])
    state["carte_adversaire"] = carte
    tirs_a_jouer = apply_card_start_bonus(connexion, partie, state, partie["id_virtuel"], carte)
    resumes = []

    for _ in range(tirs_a_jouer):
        if carte["code"] in CARDES_SANS_COORDONNEES:
            resume = execute_attack_action(connexion, partie, state, partie["id_virtuel"], carte, None)
        else:
            coordonnee = choose_ai_target(connexion, partie, state, carte)
            if coordonnee is None:
                break
            resume = execute_attack_action(connexion, partie, state, partie["id_virtuel"], carte, coordonnee)
        resumes.append(resume)
        update_ai_targets_with_resume(connexion, partie, state, resume)
        if are_all_player_ships_sunk(connexion, partie, state, partie["id_humain"]):
            break

    return {
        "carte": carte,
        "effet_message": carte.get("effet_message"),
        "actions": resumes,
    }


def are_all_player_ships_sunk(connexion, partie, state, id_joueur):
    navires = get_player_ships(connexion, partie, state, id_joueur)
    return bool(navires) and all(navire["etat"] == "coule" for navire in navires)


def update_current_tour_stats(connexion, partie, state):
    navires = get_ships_with_status(connexion, partie, state)
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    _, explorees_par_joueur = build_exploration_maps(partie, tirs)

    navires_humain = [navire for navire in navires if navire["id_joueur"] == partie["id_humain"]]
    navires_virtuel = [navire for navire in navires if navire["id_joueur"] == partie["id_virtuel"]]

    joueur_navires_coules = sum(1 for navire in navires_humain if navire["etat"] == "coule")
    joueur_navires_touches = sum(1 for navire in navires_humain if navire["etat"] in ("touche", "coule"))
    adversaire_navires_coules = sum(1 for navire in navires_virtuel if navire["etat"] == "coule")
    adversaire_navires_touches = sum(1 for navire in navires_virtuel if navire["etat"] in ("touche", "coule"))
    joueur_cases_a_explorer = max(0, 100 - len(explorees_par_joueur[partie["id_virtuel"]]))
    adversaire_cases_a_explorer = max(0, 100 - len(explorees_par_joueur[partie["id_humain"]]))

    ensure_turn_exists(connexion, partie["id_partie"], state["tour_courant"])
    with connexion.cursor() as cur:
        cur.execute(
            """
            UPDATE tour
            SET
                joueur_navires_coules = %s,
                joueur_navires_touches = %s,
                joueur_cases_a_explorer = %s,
                adversaire_navires_coules = %s,
                adversaire_navires_touches = %s,
                adversaire_cases_a_explorer = %s
            WHERE id_partie = %s
              AND num_tour = %s
            """,
            (
                joueur_navires_coules,
                joueur_navires_touches,
                joueur_cases_a_explorer,
                adversaire_navires_coules,
                adversaire_navires_touches,
                adversaire_cases_a_explorer,
                partie["id_partie"],
                state["tour_courant"],
            ),
        )


def compute_score(connexion, id_partie):
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM tir WHERE id_partie = %s AND x IS NOT NULL AND y IS NOT NULL",
            (id_partie,),
        )
        nb_tirs = cur.fetchone()[0]
    if nb_tirs <= 0:
        return 0
    return math.floor(100 * 17 / nb_tirs)


def finish_partie(connexion, partie, state, gagnant_id):
    score = compute_score(connexion, partie["id_partie"])
    etat = "gagnee" if gagnant_id == partie["id_humain"] else "perdue"
    with connexion.cursor() as cur:
        cur.execute(
            """
            UPDATE partie
            SET etat = %s, score_final = %s, id_gagnant = %s
            WHERE id_partie = %s
            """,
            (etat, score, gagnant_id, partie["id_partie"]),
        )
    close_open_sequence(connexion, partie["id_partie"])
    state["phase"] = "terminee"
    save_game_state(connexion, partie["id_partie"], state)


def start_partie(connexion, id_partie, id_joueur):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return "Partie introuvable.", False
    if partie["id_gagnant"] is not None:
        return None, True
    try:
        start_new_turn(connexion, partie, state)
    except ValueError as exc:
        return str(exc), False
    return None, True


def verifier_case_vide(connexion, id_partie, id_joueur, coordonnee_texte):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return "Partie introuvable.", False
    carte = state.get("carte_joueur")
    if state.get("phase") != "tir_joueur" or carte is None or carte["code"] != 3:
        return "Verification impossible pour ce tour.", False

    coordonnee = parse_coordonnee(coordonnee_texte)
    if coordonnee is None:
        return "Coordonnee invalide.", False

    navires = get_player_ships(connexion, partie, state, partie["id_virtuel"])
    occupied = set()
    for navire in navires:
        occupied.update(cells_from_navire(navire))
    leurres, willys = get_special_cells(state, partie["id_virtuel"])
    occupied.update(leurres)
    occupied.update(willys)

    message = "La case est occupee." if coordonnee in occupied else "La case est vide."
    state["verification_vide"] = f"Verification de {coord_to_label(coordonnee[0], coordonnee[1])} : {message}"
    save_game_state(connexion, partie["id_partie"], state)
    return None, True


def play_player_turn(connexion, id_partie, id_joueur, coordonnee_texte):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return "Partie introuvable.", False
    if state.get("phase") != "tir_joueur" or state.get("carte_joueur") is None:
        return "Le tour du joueur n'est pas actif.", False

    open_sequence_if_needed(connexion, partie["id_partie"])

    carte = state["carte_joueur"]
    coordonnee = None
    if carte["code"] not in CARDES_SANS_COORDONNEES:
        coordonnee = parse_coordonnee(coordonnee_texte)
        if coordonnee is None:
            return "Coordonnee invalide.", False
        explorees = get_attack_grid_explored(connexion, partie, partie["id_humain"])
        if coordonnee in explorees:
            return "Cette case a deja ete exploree.", False

    resume = execute_attack_action(connexion, partie, state, partie["id_humain"], carte, coordonnee)
    state["dernier_tir_joueur"] = resume
    state["verification_vide"] = None
    state["tirs_restants_joueur"] -= 1
    refresh_navires_states(connexion, partie, state)

    if are_all_player_ships_sunk(connexion, partie, state, partie["id_virtuel"]):
        update_current_tour_stats(connexion, partie, state)
        finish_partie(connexion, partie, state, partie["id_humain"])
        return None, True

    if carte["code"] == 2 and state["tirs_restants_joueur"] > 0:
        carte["effet_message"] = "Vous pouvez tirer une seconde fois grace a cette carte."
        state["carte_joueur"] = carte
        state["phase"] = "tir_joueur"
        update_current_tour_stats(connexion, partie, state)
        save_game_state(connexion, partie["id_partie"], state)
        return None, True

    state["dernier_tir_adversaire"] = execute_ai_turn(connexion, partie, state)
    refresh_navires_states(connexion, partie, state)
    update_current_tour_stats(connexion, partie, state)

    if are_all_player_ships_sunk(connexion, partie, state, partie["id_humain"]):
        finish_partie(connexion, partie, state, partie["id_virtuel"])
        state["phase"] = "attente_adversaire"
        save_game_state(connexion, partie["id_partie"], state)
        return None, True

    state["phase"] = "attente_adversaire"
    save_game_state(connexion, partie["id_partie"], state)
    return None, True


def advance_game_state(connexion, id_partie, id_joueur):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return "Partie introuvable.", False

    open_sequence_if_needed(connexion, partie["id_partie"])

    if state.get("phase") == "attente_adversaire":
        state["phase"] = "resume_adversaire"
        save_game_state(connexion, partie["id_partie"], state)
        return None, True

    if state.get("phase") == "resume_adversaire":
        if partie["id_gagnant"] is not None:
            state["phase"] = "terminee"
            save_game_state(connexion, partie["id_partie"], state)
            return None, True
        start_new_turn(connexion, partie, state)
        return None, True

    return "Le bouton Suivant n'est pas disponible.", False


def suspend_partie(connexion, id_partie, id_joueur):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return "Partie introuvable.", False
    if partie["id_gagnant"] is not None:
        return "La partie est deja terminee.", False

    with connexion.cursor() as cur:
        cur.execute("UPDATE partie SET etat = 'suspendue' WHERE id_partie = %s", (id_partie,))
    close_open_sequence(connexion, id_partie)
    save_game_state(connexion, id_partie, state)
    return None, True


def grid_value_for_template(cell_type):
    mapping = {
        "mer": "",
        "navire": "N",
        "touche": "X",
        "coule": "C",
        "eau": "o",
        "leurre": "L",
        "willy": "W",
        "inconnu": "",
        "impact_leurre": "X",
        "impact_willy": "W",
    }
    return mapping.get(cell_type, "")


def get_hidden_last_ai_cells(state):
    if state.get("phase") != "attente_adversaire":
        return set()
    dernier = state.get("dernier_tir_adversaire")
    if not dernier:
        return set()
    cellules = set()
    for action in dernier.get("actions", []):
        carte = action.get("carte") or dernier.get("carte")
        coord = parse_coordonnee(action.get("coordonnee"))
        if coord is None:
            continue
        cellules.update(attack_cells_from_code(carte["code"], coord[0], coord[1]))
    return cellules


def decoy_is_still_hidden_for_attacker(leurre, explored_by_attacker):
    hit_cell = leurre.get("hit_cell")
    if hit_cell is None:
        return False
    x, y = hit_cell
    voisins = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = x + dx
        ny = y + dy
        if cell_in_grid(nx, ny):
            voisins.append((nx, ny))
    return not all(voisin in explored_by_attacker for voisin in voisins)


def build_player_grid(connexion, partie, state, id_joueur):
    navires = get_player_ships(connexion, partie, state, id_joueur)
    tirs = get_tirs_partie(connexion, partie["id_partie"])
    explorees_sur_grille, _ = build_exploration_maps(partie, tirs)
    cellules_cachees = get_hidden_last_ai_cells(state) if id_joueur == partie["id_humain"] else set()
    explores = set(explorees_sur_grille[id_joueur]) - cellules_cachees

    grid = {(x, y): {"type": "mer", "label": "", "classes": ["cell-mer"]} for x in range(1, NB_COLONNES + 1) for y in range(1, NB_LIGNES + 1)}
    their_forced_sunk = set(state.get("navires_forces_coules", []))

    for navire in navires:
        cellules = cells_from_navire(navire)
        for cellule in cellules:
            if navire["id_navire"] in their_forced_sunk or navire["etat"] == "coule":
                grid[cellule] = {"type": "coule", "label": "C", "classes": ["cell-coule"]}
            elif cellule in explores:
                grid[cellule] = {"type": "touche", "label": "X", "classes": ["cell-touche"]}
            else:
                grid[cellule] = {"type": "navire", "label": "N", "classes": ["cell-navire"]}

    for cellule in explores:
        if grid[cellule]["type"] == "mer":
            grid[cellule] = {"type": "eau", "label": "o", "classes": ["cell-eau"]}

    for willy in state.get("willys", []):
        if willy["owner"] == id_joueur and willy.get("actif"):
            cellule = (willy["x"], willy["y"])
            if grid[cellule]["type"] == "mer":
                grid[cellule] = {"type": "willy", "label": "W", "classes": ["cell-willy"]}

    for leurre in state.get("leurres", []):
        if leurre["owner"] != id_joueur:
            continue
        if leurre.get("actif"):
            for cellule in [tuple(case) for case in leurre["cells"]]:
                if grid[cellule]["type"] == "mer":
                    grid[cellule] = {"type": "leurre", "label": "L", "classes": ["cell-leurre"]}

    return format_grid_for_template(grid)


def build_attack_grid(connexion, partie, state, id_joueur):
    navires_adverses = get_player_ships(connexion, partie, state, get_player_opponent(partie, id_joueur))
    ship_cells = {}
    forced = set(state.get("navires_forces_coules", []))
    for navire in navires_adverses:
        for cellule in cells_from_navire(navire):
            ship_cells[cellule] = {
                "etat": "coule" if navire["id_navire"] in forced or navire["etat"] == "coule" else navire["etat"],
                "id_navire": navire["id_navire"],
            }

    tirs = get_tirs_partie(connexion, partie["id_partie"])
    grid = {(x, y): {"type": "inconnu", "label": "", "classes": ["cell-inconnu"]} for x in range(1, NB_COLONNES + 1) for y in range(1, NB_LIGNES + 1)}

    for tir in tirs:
        if tir["id_joueur"] != id_joueur:
            continue
        code = tir["code_carte_type"]
        if code in CARDES_SANS_COORDONNEES or tir["x"] is None or tir["y"] is None:
            continue
        for cellule in attack_cells_from_code(code, tir["x"], tir["y"]):
            if cellule in ship_cells:
                grid[cellule] = {
                    "type": "coule" if ship_cells[cellule]["etat"] == "coule" else "touche",
                    "label": "C" if ship_cells[cellule]["etat"] == "coule" else "X",
                    "classes": ["cell-coule" if ship_cells[cellule]["etat"] == "coule" else "cell-touche"],
                }
            else:
                grid[cellule] = {"type": "eau", "label": "o", "classes": ["cell-eau"]}

    for leurre in state.get("leurres", []):
        if leurre["owner"] != get_player_opponent(partie, id_joueur):
            continue
        if leurre.get("hit_cell") and leurre.get("touched_by") == id_joueur:
            explorees = get_attack_grid_explored(connexion, partie, id_joueur)
            if decoy_is_still_hidden_for_attacker(leurre, explorees):
                cellule = tuple(leurre["hit_cell"])
                grid[cellule] = {"type": "impact_leurre", "label": "X", "classes": ["cell-touche"]}
            else:
                cellule = tuple(leurre["hit_cell"])
                grid[cellule] = {"type": "inconnu", "label": "", "classes": ["cell-inconnu"]}

    for willy in state.get("willys", []):
        if willy["owner"] != get_player_opponent(partie, id_joueur):
            continue
        if not willy.get("actif"):
            cellule = (willy["x"], willy["y"])
            if grid[cellule]["type"] == "inconnu":
                grid[cellule] = {"type": "impact_willy", "label": "W", "classes": ["cell-willy"]}

    return format_grid_for_template(grid)


def format_grid_for_template(grid):
    lignes = []
    for y in range(1, NB_LIGNES + 1):
        cellules = []
        for x in range(1, NB_COLONNES + 1):
            cellule = grid[(x, y)]
            cellules.append(
                {
                    "x": x,
                    "y": y,
                    "label": cellule["label"],
                    "classes": " ".join(["grille-case"] + cellule["classes"]),
                }
            )
        lignes.append({"numero": y, "cellules": cellules})
    return {
        "colonnes": list(COLONNES),
        "lignes": lignes,
    }


def build_final_message(partie):
    if partie["id_gagnant"] is None:
        return None
    if partie["id_gagnant"] == partie["id_humain"]:
        return f"{partie['pseudo_humain']} a gagne."
    return f"{partie['pseudo_humain']} a perdu."


def build_action_messages(detail):
    if detail is None:
        return []
    actions = detail.get("actions")
    if actions is None:
        actions = [detail]
    messages = []
    for action in actions:
        if action.get("message"):
            messages.append(action["message"])
    return messages


def get_partie_game_view(connexion, id_partie, id_joueur):
    partie, state = load_partie_for_player(connexion, id_partie, id_joueur)
    if partie is None:
        return None

    refresh_navires_states(connexion, partie, state)
    phase = state.get("phase", "creation")
    carte_joueur = state.get("carte_joueur")
    carte_adversaire_visible = state.get("carte_adversaire") if phase in ("resume_adversaire", "terminee") else None
    dernier_tir_adversaire_visible = state.get("dernier_tir_adversaire") if phase in ("resume_adversaire", "terminee") else None

    return {
        "id_partie": partie["id_partie"],
        "etat_partie": partie["etat"],
        "adversaire_pseudo": partie["pseudo_virtuel"],
        "adversaire_niveau": partie["niveau_virtuel"],
        "phase": phase,
        "tour_courant": state.get("tour_courant", 0),
        "partie_commencee": state.get("tour_courant", 0) > 0,
        "carte_joueur": carte_joueur,
        "carte_adversaire": carte_adversaire_visible,
        "verification_vide": state.get("verification_vide"),
        "dernier_tir_joueur": state.get("dernier_tir_joueur"),
        "dernier_tir_adversaire": dernier_tir_adversaire_visible,
        "grille_joueur": build_player_grid(connexion, partie, state, partie["id_humain"]),
        "grille_tirs": build_attack_grid(connexion, partie, state, partie["id_humain"]),
        "afficher_commencer": phase == "creation" and partie["id_gagnant"] is None,
        "afficher_tirer": phase == "tir_joueur" and partie["id_gagnant"] is None,
        "afficher_suivant": phase == "attente_adversaire" or (phase == "resume_adversaire" and partie["id_gagnant"] is None),
        "afficher_suspendre": phase in ("tir_joueur", "attente_adversaire", "resume_adversaire") and partie["id_gagnant"] is None,
        "coordonnees_requises": carte_joueur is not None and carte_joueur["code"] not in CARDES_SANS_COORDONNEES and phase == "tir_joueur",
        "afficher_verifier": carte_joueur is not None and carte_joueur["code"] == 3 and phase == "tir_joueur",
        "resultat_partie": build_final_message(partie),
        "messages_joueur": build_action_messages(state.get("dernier_tir_joueur")),
        "messages_adversaire": build_action_messages(dernier_tir_adversaire_visible),
    }


def get_moyenne_tours(conn, joueur_id):
    """
    Retourne le nombre moyen de tours par partie pour un joueur donne.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT AVG(nb_tours) AS moyenne_tours
        FROM (
            SELECT COUNT(*) AS nb_tours
            FROM PARTIE p
            JOIN TOUR t ON p.id_partie = t.id_partie
            WHERE p.id_humain = %s
            GROUP BY p.id_partie
        ) AS sous_requete
        """,
        (str(joueur_id),),
    )
    result = cur.fetchone()
    if result is not None and result[0] is not None:
        return result[0]
    return None


def get_joueurs_virtuels(connexion):
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.pseudo, j.id_joueur
            FROM virtuel v
            JOIN joueur j ON v.id_joueur = j.id_joueur
            ORDER BY j.pseudo
            """
        )
        return cur.fetchall()


def get_joueurs_humains(connexion):
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.pseudo, j.id_joueur
            FROM humain h
            JOIN joueur j ON h.id_joueur = j.id_joueur
            ORDER BY j.pseudo
            """
        )
        return cur.fetchall()


def get_joueurs_virtuels_like(connexion, like_pattern):
    motif = "%" + like_pattern + "%"
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.id_joueur, j.pseudo
            FROM virtuel v
            JOIN joueur j ON v.id_joueur = j.id_joueur
            WHERE j.pseudo ILIKE %s
            ORDER BY j.pseudo
            """,
            (motif,),
        )
        return cur.fetchall()


def get_joueurs_humains_like(connexion, like_pattern):
    motif = "%" + like_pattern + "%"
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.id_joueur, j.pseudo
            FROM humain h
            JOIN joueur j ON h.id_joueur = j.id_joueur
            WHERE j.pseudo ILIKE %s
            ORDER BY j.pseudo
            """,
            (motif,),
        )
        return cur.fetchall()


def is_virtuel(connexion, joueur_id):
    with connexion.cursor() as cur:
        cur.execute("SELECT 1 FROM virtuel WHERE id_joueur = %s", (joueur_id,))
        return cur.fetchone() is not None


def is_humain(connexion, joueur_id):
    with connexion.cursor() as cur:
        cur.execute("SELECT 1 FROM humain WHERE id_joueur = %s", (joueur_id,))
        return cur.fetchone() is not None


def get_parties_en_cours(connexion, joueur_id):
    """
    Retourne les parties non terminees du joueur avec les statistiques a afficher.
    """
    ensure_game_schema(connexion)
    query = """
        WITH date_creation AS (
            SELECT DISTINCT ON (st.id_partie)
                st.id_partie,
                st.date_debut,
                st.heure_debut
            FROM sequence_temporelle st
            ORDER BY st.id_partie, st.date_debut, st.heure_debut
        ),
        stats_navires AS (
            SELECT
                f.id_partie,
                f.id_joueur,
                COUNT(n.id_navire) FILTER (
                    WHERE LOWER(COALESCE(n.etat, '')) LIKE 'coul%%'
                ) AS navires_coules,
                COUNT(n.id_navire) FILTER (
                    WHERE LOWER(COALESCE(n.etat, '')) LIKE 'touch%%'
                       OR LOWER(COALESCE(n.etat, '')) LIKE 'coul%%'
                ) AS navires_touches
            FROM flotille f
            LEFT JOIN navire n ON n.id_flotille = f.id_flotille
            GROUP BY f.id_partie, f.id_joueur
        )
        SELECT
            p.id_partie,
            dc.date_debut,
            dc.heure_debut,
            jv.pseudo AS adversaire_pseudo,
            v.niveau AS adversaire_niveau,
            COUNT(DISTINCT t.num_tour) AS nb_tours,
            COALESCE(sn_joueur.navires_coules, 0) AS joueur_navires_coules,
            COALESCE(sn_joueur.navires_touches, 0) AS joueur_navires_touches,
            COALESCE(sn_adversaire.navires_coules, 0) AS adversaire_navires_coules,
            COALESCE(sn_adversaire.navires_touches, 0) AS adversaire_navires_touches,
            p.etat
        FROM partie p
        JOIN virtuel v
            ON v.id_joueur = p.id_virtuel
        JOIN joueur jv
            ON jv.id_joueur = v.id_joueur
        LEFT JOIN tour t
            ON t.id_partie = p.id_partie
        LEFT JOIN date_creation dc
            ON dc.id_partie = p.id_partie
        LEFT JOIN stats_navires sn_joueur
            ON sn_joueur.id_partie = p.id_partie
           AND sn_joueur.id_joueur = p.id_humain
        LEFT JOIN stats_navires sn_adversaire
            ON sn_adversaire.id_partie = p.id_partie
           AND sn_adversaire.id_joueur = p.id_virtuel
        WHERE p.id_humain = %s
          AND p.id_gagnant IS NULL
        GROUP BY
            p.id_partie,
            dc.date_debut,
            dc.heure_debut,
            jv.pseudo,
            v.niveau,
            sn_joueur.navires_coules,
            sn_joueur.navires_touches,
            sn_adversaire.navires_coules,
            sn_adversaire.navires_touches,
            p.etat
        ORDER BY dc.date_debut DESC NULLS LAST, dc.heure_debut DESC NULLS LAST, p.id_partie DESC
    """

    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (joueur_id,))
        parties = cur.fetchall()

    for partie in parties:
        heure = partie.get("heure_debut")
        if heure is None:
            partie["creation_affichage"] = "Date inconnue"
        else:
            heure_str = str(heure).zfill(4)
            if partie.get("date_debut"):
                partie["creation_affichage"] = (
                    f"{partie['date_debut'].strftime('%d/%m/%Y')} a {heure_str[:2]}h{heure_str[2:]}"
                )
            else:
                partie["creation_affichage"] = f"Heure {heure_str[:2]}h{heure_str[2:]}"
    return parties


def get_classement_ijh(connexion, delta_mois=0):
    """
    Classement individuel joueurs humains (IJH)
    """

    if delta_mois == 0:
        query = """
            SELECT
                j.pseudo,
                j.id_joueur,
                COALESCE(SUM(p.score_final), 0) AS score_total,
                COUNT(DISTINCT p.id_partie) AS nb_parties
            FROM humain h
            JOIN joueur j ON h.id_joueur = j.id_joueur
            LEFT JOIN partie p
                ON p.id_humain = h.id_joueur
               AND p.score_final IS NOT NULL
            GROUP BY j.id_joueur, j.pseudo
            ORDER BY score_total DESC, nb_parties DESC
        """
        params = []

    else:
        query = """
            SELECT
                j.pseudo,
                j.id_joueur,
                COALESCE(SUM(p.score_final), 0) AS score_total,
                COUNT(DISTINCT p.id_partie) AS nb_parties
            FROM humain h
            JOIN joueur j ON h.id_joueur = j.id_joueur
            LEFT JOIN partie p
                ON p.id_humain = h.id_joueur
               AND p.score_final IS NOT NULL
            LEFT JOIN sequence_temporelle st
                ON st.id_partie = p.id_partie
               AND st.date_debut >= CURRENT_DATE - make_interval(months => %s)
            GROUP BY j.id_joueur, j.pseudo
            ORDER BY score_total DESC, nb_parties DESC
        """
        params = [delta_mois]

    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()

def get_classement_cpp(connexion, delta_mois=0):
    """
    Classement par pavillon (CPP)
    """

    if delta_mois == 0:
        query = """
            SELECT
                f.pavillon,
                COALESCE(SUM(p.score_final), 0) AS score_total,
                COUNT(DISTINCT p.id_partie) AS nb_parties,
                COUNT(DISTINCT p.id_humain) AS nb_joueurs
            FROM flotille f
            JOIN partie p
                ON p.id_partie = f.id_partie
               AND p.score_final IS NOT NULL
            JOIN humain h
                ON h.id_joueur = p.id_humain
            WHERE LOWER(TRIM(f.pavillon)) != 'coalition'
            GROUP BY f.pavillon
            ORDER BY score_total DESC, nb_parties DESC
        """
        params = []

    else:
        query = """
            SELECT
                f.pavillon,
                COALESCE(SUM(p.score_final), 0) AS score_total,
                COUNT(DISTINCT p.id_partie) AS nb_parties,
                COUNT(DISTINCT p.id_humain) AS nb_joueurs
            FROM flotille f
            JOIN partie p
                ON p.id_partie = f.id_partie
               AND p.score_final IS NOT NULL
            JOIN humain h
                ON h.id_joueur = p.id_humain
            LEFT JOIN sequence_temporelle st
                ON st.id_partie = p.id_partie
               AND st.date_debut >= CURRENT_DATE - make_interval(months => %s)
            WHERE LOWER(TRIM(f.pavillon)) != 'coalition'
            GROUP BY f.pavillon
            ORDER BY score_total DESC, nb_parties DESC
        """
        params = [delta_mois]

    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()