from model.model_pg import get_moyenne_tours

if SESSION.get('JOUEUR_ID'):
    joueur_id = SESSION['JOUEUR_ID']
    moyenne = get_moyenne_tours(SESSION['CONNEXION'], joueur_id)
    if moyenne is None:    # aucune partie jouée
        moyenne = 0
    REQUEST_VARS['moyenne_tours'] = moyenne
else:
    REQUEST_VARS['moyenne_tours'] = 0