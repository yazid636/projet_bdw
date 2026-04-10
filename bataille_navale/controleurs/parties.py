REQUEST_VARS['joueurs_virtuels'] = None

cur = SESSION['CONNEXION'].cursor()
cur.execute("SELECT j.pseudo, j.id_joueur FROM virtuel v JOIN joueur j ON v.id_joueur = j.id_joueur")
REQUEST_VARS['joueurs_virtuels'] = cur.fetchall()

if POST and 'ajouter_virtuel' in POST:
    nouveau_pseudo = POST.get('nouveau_pseudo', [None])[0]
    niveau = POST.get('niveau', [None])[0]
    id_createur = SESSION['JOUEUR_ID']

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
                """INSERT INTO virtuel (id_joueur, niveau, id_createur, date_creation)
                   VALUES (%s, %s, %s, CURRENT_DATE)""",
                (nouveau_id, niveau, id_createur)
            )

if POST and 'creer_partie' in POST:
    id_humain = SESSION['JOUEUR_ID']
    id_virtuel = POST.get('id_virtuel', [None])[0]

    if not all([id_humain, id_virtuel]):
        REQUEST_VARS['erreur_creation'] = "Tous les champs sont obligatoires."
    else:
        cur.execute("SELECT COALESCE(MAX(id_partie), 0) + 1 FROM partie")
        id_partie = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO partie (id_partie, id_humain, id_virtuel) VALUES (%s, %s, %s)",
            (id_partie, id_humain, id_virtuel)
        )