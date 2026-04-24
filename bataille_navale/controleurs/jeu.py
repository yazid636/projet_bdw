import importlib
import model.model_pg as model_pg

model_pg = importlib.reload(model_pg)

REQUEST_VARS["erreur"] = None
REQUEST_VARS["message"] = None
REQUEST_VARS["message_class"] = None
REQUEST_VARS["jeu"] = None

if not SESSION.get("JOUEUR_ID"):
    REQUEST_VARS["erreur"] = "Vous devez vous connecter avant de jouer."
else:
    id_partie = None

    if GET and GET.get("id_partie"):
        id_partie = GET["id_partie"][0]
        SESSION["ID_PARTIE_COURANTE"] = id_partie
    elif POST and POST.get("id_partie"):
        id_partie = POST["id_partie"][0]
        SESSION["ID_PARTIE_COURANTE"] = id_partie
    elif SESSION.get("ID_PARTIE_COURANTE"):
        id_partie = SESSION["ID_PARTIE_COURANTE"]

    if id_partie is None:
        REQUEST_VARS["erreur"] = "Aucune partie n'a ete selectionnee."
    else:
        if POST and "commencer_partie" in POST:
            erreur, succes = model_pg.start_partie(SESSION["CONNEXION"], id_partie, SESSION["JOUEUR_ID"])
            if not succes:
                REQUEST_VARS["erreur"] = erreur
        elif POST and "verifier_case" in POST:
            coordonnee = POST.get("coordonnee", [""])[0]
            erreur, succes = model_pg.verifier_case_vide(
                SESSION["CONNEXION"],
                id_partie,
                SESSION["JOUEUR_ID"],
                coordonnee,
            )
            if not succes:
                REQUEST_VARS["erreur"] = erreur
        elif POST and "tirer" in POST:
            coordonnee = POST.get("coordonnee", [""])[0]
            erreur, succes = model_pg.play_player_turn(
                SESSION["CONNEXION"],
                id_partie,
                SESSION["JOUEUR_ID"],
                coordonnee,
            )
            if not succes:
                REQUEST_VARS["erreur"] = erreur
        elif POST and "suivant" in POST:
            erreur, succes = model_pg.advance_game_state(
                SESSION["CONNEXION"],
                id_partie,
                SESSION["JOUEUR_ID"],
            )
            if not succes:
                REQUEST_VARS["erreur"] = erreur
        elif POST and "suspendre_partie" in POST:
            erreur, succes = model_pg.suspend_partie(
                SESSION["CONNEXION"],
                id_partie,
                SESSION["JOUEUR_ID"],
            )
            if succes:
                REQUEST_VARS["message"] = "La partie a bien ete suspendue."
                REQUEST_VARS["message_class"] = "alert-success"
            else:
                REQUEST_VARS["erreur"] = erreur

        REQUEST_VARS["jeu"] = model_pg.get_partie_game_view(
            SESSION["CONNEXION"],
            id_partie,
            SESSION["JOUEUR_ID"],
        )

        if REQUEST_VARS["jeu"] is None and REQUEST_VARS["erreur"] is None:
            REQUEST_VARS["erreur"] = "Impossible de charger cette partie."
