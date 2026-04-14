import importlib
import model.model_pg as model_pg

model_pg = importlib.reload(model_pg)

REQUEST_VARS['joueurs_virtuels'] = []
REQUEST_VARS['parties_en_cours'] = []
REQUEST_VARS['erreur_creation'] = None
REQUEST_VARS['joueur_connecte'] = bool(SESSION.get('JOUEUR_ID'))
REQUEST_VARS['joueur_humain'] = False

if REQUEST_VARS['joueur_connecte']:
    REQUEST_VARS['joueur_humain'] = model_pg.is_humain(
        SESSION['CONNEXION'],
        SESSION['JOUEUR_ID']
    )

    if REQUEST_VARS['joueur_humain']:
        REQUEST_VARS['joueurs_virtuels'] = model_pg.get_joueurs_virtuels(SESSION['CONNEXION'])

        if POST and 'ajouter_virtuel' in POST:
            nouveau_pseudo = POST.get('nouveau_pseudo', [None])[0]
            niveau = POST.get('niveau', [None])[0]
            id_createur = SESSION.get('JOUEUR_ID')

            if not all([nouveau_pseudo, niveau]):
                REQUEST_VARS['erreur_creation'] = "Tous les champs sont obligatoires."
            else:
                cur = SESSION['CONNEXION'].cursor()
                cur.execute("SELECT id_joueur FROM joueur WHERE pseudo = %s", (nouveau_pseudo,))
                existe = cur.fetchone()
                if existe:
                    REQUEST_VARS['erreur_creation'] = "Ce pseudo est déjà utilisé."
                else:
                    cur.execute("SELECT COALESCE(MAX(id_joueur), 0) + 1 FROM joueur")
                    nouveau_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO joueur (id_joueur, pseudo) VALUES (%s, %s)",
                        (nouveau_id, nouveau_pseudo)
                    )
                    cur.execute(
                        """
                        INSERT INTO virtuel (id_joueur, niveau, id_createur, date_creation)
                        VALUES (%s, %s, %s, CURRENT_DATE)
                        """,
                        (nouveau_id, niveau, id_createur)
                    )
                    REQUEST_VARS['joueurs_virtuels'] = model_pg.get_joueurs_virtuels(SESSION['CONNEXION'])

        if POST and 'creer_partie' in POST:
            id_humain = SESSION.get('JOUEUR_ID')
            id_virtuel = POST.get('id_virtuel', [None])[0]

            if not id_virtuel:
                REQUEST_VARS['erreur_creation'] = "Vous devez sélectionner un adversaire."
            else:
                model_pg.create_partie(SESSION['CONNEXION'], id_humain, id_virtuel)

        REQUEST_VARS['parties_en_cours'] = model_pg.get_parties_en_cours(
            SESSION['CONNEXION'],
            SESSION['JOUEUR_ID']
        )
    else:
        REQUEST_VARS['erreur_creation'] = (
            "Seul un joueur humain peut créer ou reprendre des parties. "
            "Connectez-vous avec un joueur humain."
        )
else:
    REQUEST_VARS['erreur_creation'] = "Vous devez vous connecter pour accéder aux parties."
