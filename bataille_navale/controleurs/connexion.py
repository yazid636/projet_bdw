from model.model_pg import get_joueurs

REQUEST_VARS['joueurs'] = get_joueurs(SESSION['CONNEXION'], 'joueur')
REQUEST_VARS['resultats'] = None
REQUEST_VARS['erreur_creation'] = None

if POST and 'bouton_valider' in POST:
    term = POST['recherche']
    term = term[0]
    cur = SESSION['CONNEXION'].cursor()
    cur.execute("SELECT id_joueur, pseudo FROM joueur WHERE pseudo ILIKE %s", ('%' + term + '%',))
    REQUEST_VARS['resultats'] = cur.fetchall()

if POST and 'choisir_joueur' in POST:
    joueur_id = POST['joueur_id']
    joueur_id = joueur_id[0]
    cur = SESSION['CONNEXION'].cursor()
    cur.execute("SELECT id_joueur, pseudo FROM joueur WHERE id_joueur = %s", (joueur_id,))
    joueur = cur.fetchone()
    if joueur:
        SESSION['JOUEUR_ID'] = joueur[0]
        SESSION['PSEUDO'] = joueur[1]

if POST and 'ajouter_joueur' in POST:
    nouveau_pseudo = POST.get('nouveau_pseudo', [None])[0]
    nouveau_nom    = POST.get('nouveau_nom',    [None])[0]
    nouveau_prenom = POST.get('nouveau_prenom', [None])[0]
    nouvelle_ddn   = POST.get('nouvelle_ddn',   [None])[0]

    if not all([nouveau_pseudo, nouveau_nom, nouveau_prenom, nouvelle_ddn]):
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
                """INSERT INTO humain (id_joueur, nom, prenom, date_de_naissance, date_de_creation)
                   VALUES (%s, %s, %s, %s, CURRENT_DATE)""",
                (nouveau_id, nouveau_nom, nouveau_prenom, nouvelle_ddn)
            )
            SESSION['CONNEXION'].commit()
            SESSION['JOUEUR_ID'] = nouveau_id
            SESSION['PSEUDO'] = nouveau_pseudo
