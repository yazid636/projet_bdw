from model.model_pg import get_moyenne_tours

if SESSION.get('JOUEUR_ID'):
    joueur_id = SESSION['JOUEUR_ID']
    moyenne = get_moyenne_tours(SESSION['CONNEXION'], joueur_id)
    if moyenne is not None:
        moyenne = round(moyenne, 2)
    else:
        moyenne = None
    REQUEST_VARS['moyenne_tours'] = moyenne
else:
    REQUEST_VARS['moyenne_tours'] = None