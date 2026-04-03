from model.model_pg import get_joueurs

REQUEST_VARS['joueurs'] = get_joueurs(SESSION['CONNEXION'], 'joueur')

if POST and 'bouton_valider' in POST:
    term = POST['recherche']
    term = term[0]
    cur = SESSION['CONNEXION'].cursor()
    cur.execute("SELECT * FROM joueur WHERE pseudo ILIKE %s", ('%' + term + '%',))
    REQUEST_VARS['resultats'] = cur.fetchall()

if POST and 'choisir_joueur' in POST:
    joueur_id = POST['joueur_id']
    joueur_id = joueur_id[0]
    cur = SESSION['CONNEXION'].cursor()
    cur.execute("SELECT id, pseudo FROM joueur WHERE id = %s", (joueur_id,))
    joueur = cur.fetchone()
    if joueur:
        SESSION['JOUEUR_ID'] = joueur[0]
        SESSION['PSEUDO'] = joueur[1]

if POST and 'ajouter_joueur' in POST:
    nouveau_pseudo = POST['nouveau_pseudo']
    if isinstance(nouveau_pseudo, list):
        nouveau_pseudo = nouveau_pseudo[0]
    if nouveau_pseudo:
        cur = SESSION['CONNEXION'].cursor()
        cur.execute("SELECT id FROM joueur WHERE pseudo = %s", (nouveau_pseudo,))
        existe = cur.fetchone()
        if not existe:
            cur.execute("SELECT COALESCE(MAX(CAST(id AS INTEGER)), 0) + 1 FROM joueur")
            nouveau_id = cur.fetchone()[0]   # c'est maintenant un entier
            cur.execute("INSERT INTO joueur (id, pseudo) VALUES (%s, %s)",(nouveau_id, nouveau_pseudo))
            SESSION['CONNEXION'].commit()
            SESSION['JOUEUR_ID'] = nouveau_id
            SESSION['PSEUDO'] = nouveau_pseudo