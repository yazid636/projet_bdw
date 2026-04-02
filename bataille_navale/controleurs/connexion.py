from model.model_pg import get_joueurs
from controleurs.includes import add_activity

add_activity(SESSION['HISTORIQUE'], "affichage des données")

REQUEST_VARS['joueurs'] = get_joueurs(SESSION['CONNEXION'], 'joueur')

if POST and 'bouton_valider' in POST:
    term = POST['recherche']
    if isinstance(term, list):
        term = term[0]

    if not isinstance(term, str):
        term = str(term)

    cur = SESSION['CONNEXION'].cursor()
    cur.execute(
        "SELECT * FROM joueur WHERE pseudo ILIKE %s",
        ('%' + term + '%',)
    )
    REQUEST_VARS['resultats'] = cur.fetchall()

if POST and 'choisir_joueur' in POST:
    joueur_id = POST['joueur_id']
    if isinstance(joueur_id, list):
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
    nouveau_pseudo = nouveau_pseudo.strip()

    if nouveau_pseudo:
        cur = SESSION['CONNEXION'].cursor()

        # Vérifier si le pseudo existe déjà
        cur.execute("SELECT id FROM joueur WHERE pseudo = %s", (nouveau_pseudo,))
        existe = cur.fetchone()

        if not existe:
            # === CALCUL DE L'ID (id est de type TEXT) ===
            cur.execute("SELECT COALESCE(MAX(CAST(id AS INTEGER)), 0) + 1 FROM joueur")
            nouveau_id = cur.fetchone()[0]   # c'est maintenant un entier

            # Insertion (PostgreSQL convertira automatiquement l'entier en texte)
            cur.execute(
                "INSERT INTO joueur (id, pseudo) VALUES (%s, %s)",
                (nouveau_id, nouveau_pseudo)
            )
            SESSION['CONNEXION'].commit()

            # Connexion automatique
            SESSION['JOUEUR_ID'] = nouveau_id
            SESSION['PSEUDO'] = nouveau_pseudo