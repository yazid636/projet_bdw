from model.model_pg import get_joueurs
from controleurs.includes import add_activity

add_activity(SESSION['HISTORIQUE'], "affichage des données")

REQUEST_VARS['joueurs'] = get_joueurs(SESSION['CONNEXION'], 'joueur')

if POST and 'bouton_valider' in POST:
    term = POST['recherche'][0]  # récupère le texte
    cur = SESSION['CONNEXION'].cursor()
    cur.execute(
        "SELECT * FROM joueur WHERE pseudo ILIKE %s",
        ('%' + term + '%',)
    )
    REQUEST_VARS['resultats'] = cur.fetchall()
