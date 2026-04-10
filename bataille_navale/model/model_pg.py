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
