import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from logzero import logger

def execute_select_query(connexion, query, params=[]):
    """
    Méthode générique pour exécuter une requête SELECT (qui peut retourner plusieurs instances).
    """
    with connexion.cursor() as cursor:
        try:
            cursor.execute(query, params)
            cursor.row_factory = dict_row
            result = cursor.fetchall()
            return result
        except psycopg.Error as e:
            logger.error(e)
    return None

def execute_other_query(connexion, query, params=[]):
    """
    Méthode générique pour exécuter une requête INSERT, UPDATE, DELETE.
    """
    with connexion.cursor() as cursor:
        try:
            cursor.execute(query, params)
            result = cursor.rowcount
            return result
        except psycopg.Error as e:
            logger.error(e)
    return None

def get_instances(connexion, nom_table):
    """
    Retourne toutes les instances de la table nom_table.
    """
    query = sql.SQL('SELECT * FROM {table}').format(table=sql.Identifier(nom_table))
    return execute_select_query(connexion, query)

def count_instances(connexion, nom_table):
    """
    Retourne le nombre d'instances de la table nom_table.
    """
    query = sql.SQL('SELECT COUNT(*) AS nb FROM {table}').format(table=sql.Identifier(nom_table))
    return execute_select_query(connexion, query)

def get_joueurs(connexion, nom_table):
    """
    Retourne tous les joueurs de la table spécifiée.
    """
    query = sql.SQL('SELECT * FROM {table}').format(table=sql.Identifier(nom_table))
    return execute_select_query(connexion, query)

def get_table_like(connexion, nom_table, like_pattern):
    """
    Retourne les instances de la table dont le pseudo correspond au motif like_pattern.
    Fonctionne sur la colonne 'pseudo' pour la table joueur.
    """
    motif = '%' + like_pattern + '%'
    # La table JOUEUR utilise la colonne 'pseudo'
    nom_att = 'pseudo'
    query = sql.SQL("SELECT * FROM {} WHERE {} ILIKE {}").format(
        sql.Identifier(nom_table),
        sql.Identifier(nom_att),
        sql.Placeholder()
    )
    return execute_select_query(connexion, query, [motif])

def get_moyenne_tours(conn, joueur_id):
    """
    Retourne le nombre moyen de tours par partie pour un joueur donné.
    Utilise id_partie (clé primaire de PARTIE) et id_humain (FK vers HUMAIN).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT AVG(nb_tours) AS moyenne_tours
        FROM (
            SELECT COUNT(*) AS nb_tours
            FROM PARTIE p
            JOIN TOUR t ON p.id_partie = t.id_partie
            WHERE p.id_humain = %s
            GROUP BY p.id_partie
        ) AS sous_requete
    """, (str(joueur_id),))
    result = cur.fetchone()
    if result is not None and result[0] is not None:
        return result[0]
    else:
        return None

def get_joueurs_virtuels(connexion):
    """
    Retourne la liste des joueurs virtuels avec leur pseudo.
    """
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
    """
    Retourne la liste des joueurs humains avec leur pseudo.
    """
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
    """
    Retourne les joueurs virtuels dont le pseudo correspond au motif.
    """
    motif = '%' + like_pattern + '%'
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.id_joueur, j.pseudo
            FROM virtuel v
            JOIN joueur j ON v.id_joueur = j.id_joueur
            WHERE j.pseudo ILIKE %s
            ORDER BY j.pseudo
            """,
            (motif,)
        )
        return cur.fetchall()

def get_joueurs_humains_like(connexion, like_pattern):
    """
    Retourne les joueurs humains dont le pseudo correspond au motif.
    """
    motif = '%' + like_pattern + '%'
    with connexion.cursor() as cur:
        cur.execute(
            """
            SELECT j.id_joueur, j.pseudo
            FROM humain h
            JOIN joueur j ON h.id_joueur = j.id_joueur
            WHERE j.pseudo ILIKE %s
            ORDER BY j.pseudo
            """,
            (motif,)
        )
        return cur.fetchall()

def is_virtuel(connexion, joueur_id):
    """
    Indique si l'identifiant correspond à un joueur virtuel.
    """
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM virtuel WHERE id_joueur = %s",
            (joueur_id,)
        )
        return cur.fetchone() is not None

def is_humain(connexion, joueur_id):
    """
    Indique si l'identifiant correspond à un joueur humain.
    """
    with connexion.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM humain WHERE id_joueur = %s",
            (joueur_id,)
        )
        return cur.fetchone() is not None

def create_partie(connexion, id_humain, id_virtuel):
    """
    Crée une nouvelle partie et enregistre sa date de début.
    """
    with connexion.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id_partie), 0) + 1 FROM partie")
        id_partie = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO partie (id_partie, id_humain, id_virtuel) VALUES (%s, %s, %s)",
            (id_partie, id_humain, id_virtuel)
        )
        cur.execute(
            """
            INSERT INTO sequence_temporelle (date_debut, heure_debut, id_partie)
            VALUES (
                CURRENT_DATE,
                CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER),
                %s
            )
            """,
            (id_partie,)
        )
        return id_partie

def get_parties_en_cours(connexion, joueur_id):
    """
    Retourne les parties en cours du joueur avec les statistiques à afficher.
    """
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
            COALESCE(sn_adversaire.navires_touches, 0) AS adversaire_navires_touches
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
            sn_adversaire.navires_touches
        ORDER BY dc.date_debut DESC NULLS LAST, dc.heure_debut DESC NULLS LAST, p.id_partie DESC
    """

    with connexion.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (joueur_id,))
        parties = cur.fetchall()

    for partie in parties:
        heure = partie.get('heure_debut')
        if heure is None:
            partie['creation_affichage'] = "Date inconnue"
            continue

        heure_str = str(heure).zfill(4)
        if partie.get('date_debut'):
            partie['creation_affichage'] = (
                f"{partie['date_debut'].strftime('%d/%m/%Y')} a {heure_str[:2]}h{heure_str[2:]}"
            )
        else:
            partie['creation_affichage'] = f"Heure {heure_str[:2]}h{heure_str[2:]}"

    return parties
