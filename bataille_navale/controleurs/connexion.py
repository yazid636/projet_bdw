from model.model_pg import get_joueurs
from controleurs.includes import add_activity

add_activity(SESSION['HISTORIQUE'], "affichage des données")

REQUEST_VARS['joueurs'] = get_joueurs(SESSION['CONNEXION'], 'joueur')
