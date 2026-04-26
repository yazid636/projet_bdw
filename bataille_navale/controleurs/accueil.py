import importlib
import model.model_pg as model_pg

model_pg = importlib.reload(model_pg)

if SESSION.get('JOUEUR_ID'):
    joueur_id = SESSION['JOUEUR_ID']
    moyenne = model_pg.get_moyenne_tours(SESSION['CONNEXION'], joueur_id)
    if moyenne is not None:
        moyenne = round(moyenne, 2)
    else:
        moyenne = None
    REQUEST_VARS['moyenne_tours'] = moyenne
    REQUEST_VARS['stats_accueil'] = model_pg.get_stats_accueil(SESSION['CONNEXION'], joueur_id)
else:
    REQUEST_VARS['moyenne_tours'] = None
    REQUEST_VARS['stats_accueil'] = None
