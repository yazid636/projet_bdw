-- Requêtes SQL demandées pendant le projet
-- Les paramètres %s correspondent aux valeurs passées par le code Python avec psycopg

-- Ajout de la colonne JSON d’état de jeu si besoin
ALTER TABLE partie ADD COLUMN IF NOT EXISTS etat_jeu TEXT;

-- Ajout du compteur de navires coulés du joueur si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_navires_coules INT DEFAULT 0;

-- Ajout du compteur de navires touchés du joueur si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_navires_touches INT DEFAULT 0;

-- Ajout du compteur de cases à explorer du joueur si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS joueur_cases_a_explorer INT DEFAULT 100;

-- Ajout du compteur de navires coulés de l’adversaire si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_navires_coules INT DEFAULT 0;

-- Ajout du compteur de navires touchés de l’adversaire si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_navires_touches INT DEFAULT 0;

-- Ajout du compteur de cases à explorer de l’adversaire si besoin
ALTER TABLE tour ADD COLUMN IF NOT EXISTS adversaire_cases_a_explorer INT DEFAULT 100;

-- Liste des joueurs humains
SELECT j.pseudo, j.id_joueur
FROM humain h
JOIN joueur j ON h.id_joueur = j.id_joueur
ORDER BY j.pseudo;

-- Recherche d’un joueur humain à partir du pseudo
SELECT j.id_joueur, j.pseudo
FROM humain h
JOIN joueur j ON h.id_joueur = j.id_joueur
WHERE j.pseudo ILIKE %s
ORDER BY j.pseudo;

-- Vérification qu’un joueur est humain
SELECT 1 FROM humain WHERE id_joueur = %s;

-- Chargement du joueur sélectionné
SELECT id_joueur, pseudo FROM joueur WHERE id_joueur = %s;

-- Vérification qu’un pseudo n’est pas déjà utilisé
SELECT id_joueur FROM joueur WHERE pseudo = %s;

-- Création d’un nouvel identifiant de joueur
SELECT COALESCE(MAX(id_joueur), 0) + 1 FROM joueur;

-- Ajout d’un joueur dans la table générale
INSERT INTO joueur (id_joueur, pseudo) VALUES (%s, %s);

-- Ajout d’un joueur humain
INSERT INTO humain (id_joueur, nom, prenom, date_de_naissance, date_de_creation)
VALUES (%s, %s, %s, %s, CURRENT_DATE);

-- Nombre de parties finies sur les trois derniers mois
SELECT COUNT(DISTINCT p.id_partie) AS nb
FROM partie p
WHERE p.id_humain = %s
  AND p.score_final IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM sequence_temporelle st
      WHERE st.id_partie = p.id_partie
        AND st.date_fin >= CURRENT_DATE - INTERVAL '3 months'
  );

-- Nombre de parties gagnées par niveau de l’adversaire
SELECT niveau, COUNT(*) AS nb
FROM (
    SELECT
        CASE
            WHEN v.niveau = 'novice' THEN 'faible'
            ELSE v.niveau
        END AS niveau
    FROM partie p
    JOIN virtuel v ON v.id_joueur = p.id_virtuel
    WHERE p.id_humain = %s
      AND p.id_gagnant = p.id_humain
) AS parties_gagnees
GROUP BY niveau
ORDER BY
    CASE
        WHEN niveau = 'faible' THEN 1
        WHEN niveau = 'intermediaire' THEN 2
        WHEN niveau = 'expert' THEN 3
        ELSE 4
    END;

-- Nombre moyen de tours par partie
SELECT AVG(nb_tours) AS moyenne_tours
FROM (
    SELECT COUNT(*) AS nb_tours
    FROM PARTIE p
    JOIN TOUR t ON p.id_partie = t.id_partie
    WHERE p.id_humain = %s
    GROUP BY p.id_partie
) AS sous_requete;

-- Points cumulés sur les parties avec une séquence temporelle en 2026
SELECT COALESCE(SUM(p.score_final), 0) AS total
FROM partie p
WHERE p.id_humain = %s
  AND p.score_final IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM sequence_temporelle st
      WHERE st.id_partie = p.id_partie
        AND (
            EXTRACT(YEAR FROM st.date_debut) = 2026
            OR EXTRACT(YEAR FROM st.date_fin) = 2026
        )
  );

-- Nombre de cartes tirées par type par le joueur courant
SELECT tc.nom, COUNT(*) AS nb
FROM tir t
JOIN carte c ON c.id_carte = t.id_carte
JOIN type_carte tc ON tc.code = c.code
WHERE t.id_joueur = %s
GROUP BY c.code, tc.nom
ORDER BY c.code;

-- Nombre d’étoiles de la mort tirées sur les dix dernières parties commencées
WITH dernieres_parties AS (
    SELECT p.id_partie
    FROM partie p
    JOIN sequence_temporelle st ON st.id_partie = p.id_partie
    GROUP BY p.id_partie
    ORDER BY MIN(st.date_debut) DESC, MIN(st.heure_debut) DESC
    LIMIT 10
)
SELECT COUNT(*) AS nb
FROM tir t
JOIN carte c ON c.id_carte = t.id_carte
WHERE c.code = 8
  AND t.id_partie IN (
      SELECT id_partie FROM dernieres_parties
  );

-- Liste des parties en cours du joueur courant
WITH date_creation AS (
    SELECT DISTINCT ON (st.id_partie)
        st.id_partie,
        st.date_debut,
        st.heure_debut
    FROM sequence_temporelle st
    ORDER BY st.id_partie, st.date_debut, st.heure_debut
),
stats_navires AS (
    SELECT
        f.id_partie,
        f.id_joueur,
        COUNT(n.id_navire) FILTER (
            WHERE LOWER(COALESCE(n.etat, '')) LIKE 'coul%%'
        ) AS navires_coules,
        COUNT(n.id_navire) FILTER (
            WHERE LOWER(COALESCE(n.etat, '')) LIKE 'touch%%'
               OR LOWER(COALESCE(n.etat, '')) LIKE 'coul%%'
        ) AS navires_touches
    FROM flotille f
    LEFT JOIN navire n ON n.id_flotille = f.id_flotille
    GROUP BY f.id_partie, f.id_joueur
)
SELECT
    p.id_partie,
    dc.date_debut,
    dc.heure_debut,
    jv.pseudo AS adversaire_pseudo,
        CASE
            WHEN v.niveau = 'novice' THEN 'faible'
            ELSE v.niveau
        END AS adversaire_niveau,
    COUNT(DISTINCT t.num_tour) AS nb_tours,
    COALESCE(sn_joueur.navires_coules, 0) AS joueur_navires_coules,
    COALESCE(sn_joueur.navires_touches, 0) AS joueur_navires_touches,
    COALESCE(sn_adversaire.navires_coules, 0) AS adversaire_navires_coules,
    COALESCE(sn_adversaire.navires_touches, 0) AS adversaire_navires_touches,
    p.etat
FROM partie p
JOIN virtuel v
    ON v.id_joueur = p.id_virtuel
JOIN joueur jv
    ON jv.id_joueur = v.id_joueur
LEFT JOIN tour t
    ON t.id_partie = p.id_partie
LEFT JOIN date_creation dc
    ON dc.id_partie = p.id_partie
LEFT JOIN stats_navires sn_joueur
    ON sn_joueur.id_partie = p.id_partie
   AND sn_joueur.id_joueur = p.id_humain
LEFT JOIN stats_navires sn_adversaire
    ON sn_adversaire.id_partie = p.id_partie
   AND sn_adversaire.id_joueur = p.id_virtuel
WHERE p.id_humain = %s
  AND p.id_gagnant IS NULL
GROUP BY
    p.id_partie,
    dc.date_debut,
    dc.heure_debut,
    jv.pseudo,
    CASE
        WHEN v.niveau = 'novice' THEN 'faible'
        ELSE v.niveau
    END,
    sn_joueur.navires_coules,
    sn_joueur.navires_touches,
    sn_adversaire.navires_coules,
    sn_adversaire.navires_touches,
    p.etat
ORDER BY dc.date_debut DESC NULLS LAST, dc.heure_debut DESC NULLS LAST, p.id_partie DESC;

-- Liste des joueurs virtuels
SELECT j.pseudo, j.id_joueur
FROM virtuel v
JOIN joueur j ON v.id_joueur = j.id_joueur
ORDER BY j.pseudo;

-- Liste des joueurs virtuels classés par niveau
SELECT
    j.pseudo,
    j.id_joueur,
    CASE
        WHEN v.niveau = 'novice' THEN 'faible'
        ELSE v.niveau
    END AS niveau
FROM virtuel v
JOIN joueur j ON v.id_joueur = j.id_joueur
ORDER BY
    CASE
        WHEN v.niveau IN ('faible', 'novice') THEN 1
        WHEN v.niveau = 'intermediaire' THEN 2
        WHEN v.niveau = 'expert' THEN 3
        ELSE 4
    END,
    j.pseudo;

-- Recherche d’un joueur virtuel à partir du pseudo
SELECT j.id_joueur, j.pseudo
FROM virtuel v
JOIN joueur j ON v.id_joueur = j.id_joueur
WHERE j.pseudo ILIKE %s
ORDER BY j.pseudo;

-- Vérification qu’un joueur est virtuel
SELECT 1 FROM virtuel WHERE id_joueur = %s;

-- Ajout d’un joueur virtuel
INSERT INTO virtuel (id_joueur, niveau, id_createur, date_creation)
VALUES (%s, %s, %s, CURRENT_DATE);

-- Recherche d’une pioche modèle disponible
SELECT p.id_pioche
FROM pioche p
WHERE EXISTS (
    SELECT 1
    FROM appartient a
    WHERE a.id_pioche = p.id_pioche
)
ORDER BY CASE WHEN p.id_pioche = 105 THEN 0 ELSE 1 END, p.id_pioche
LIMIT 1;

-- Création d’un nouvel identifiant de pioche
SELECT COALESCE(MAX(id_pioche), 0) + 1 FROM pioche;

-- Récupération du nom de la pioche modèle
SELECT nom_distrib FROM pioche WHERE id_pioche = %s;

-- Création d’une pioche pour une nouvelle partie
INSERT INTO pioche (id_pioche, nom_distrib) VALUES (%s, %s);

-- Copie de la distribution d’une pioche modèle
INSERT INTO a_pour_distribution (id_pioche, code, pourcentage)
SELECT %s, code, pourcentage
FROM a_pour_distribution
WHERE id_pioche = %s;

-- Récupération des cartes d’une pioche modèle avant mélange en Python
SELECT id_carte FROM appartient WHERE id_pioche = %s ORDER BY id_carte;

-- Ajout d’une carte dans la pioche de partie après mélange en Python
INSERT INTO appartient (id_carte, rang, id_pioche, etat)
VALUES (%s, %s, %s, %s);

-- Vérification qu’une pioche contient des cartes
SELECT COUNT(*) FROM appartient WHERE id_pioche = %s;

-- Rattachement d’une nouvelle pioche à une partie existante
UPDATE partie SET id_pioche = %s WHERE id_partie = %s;

-- Suppression des cartes d’une pioche avant réinitialisation
DELETE FROM appartient WHERE id_pioche = %s;

-- Création d’un nouvel identifiant de partie
SELECT COALESCE(MAX(id_partie), 0) + 1 FROM partie;

-- Création d’une nouvelle partie
INSERT INTO partie (
    id_partie,
    etat,
    score_final,
    id_humain,
    id_virtuel,
    id_pioche,
    id_gagnant,
    etat_jeu
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s);

-- Création de la première séquence temporelle d’une partie
INSERT INTO sequence_temporelle (date_debut, heure_debut, date_fin, heure_fin, id_partie)
VALUES (
    CURRENT_DATE,
    CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER),
    NULL,
    NULL,
    %s
);

-- Chargement des informations générales d’une partie
SELECT
    p.*,
    jh.pseudo AS pseudo_humain,
    jv.pseudo AS pseudo_virtuel,
    CASE
        WHEN v.niveau = 'novice' THEN 'faible'
        ELSE v.niveau
    END AS niveau_virtuel
FROM partie p
JOIN joueur jh ON jh.id_joueur = p.id_humain
JOIN joueur jv ON jv.id_joueur = p.id_virtuel
JOIN virtuel v ON v.id_joueur = p.id_virtuel
WHERE p.id_partie = %s;

-- Sauvegarde de l’état JSON d’une partie
UPDATE partie SET etat_jeu = %s WHERE id_partie = %s;

-- Récupération du nombre de tours d’une partie
SELECT COALESCE(MAX(num_tour), 0) FROM tour WHERE id_partie = %s;

-- Récupération du nombre de flottilles d’une partie
SELECT COUNT(*) FROM flotille WHERE id_partie = %s;

-- Chargement des navires d’une partie
SELECT
    n.*,
    f.id_joueur
FROM navire n
JOIN flotille f ON f.id_flotille = n.id_flotille
WHERE f.id_partie = %s
ORDER BY n.id_navire;

-- Chargement des tirs d’une partie
SELECT
    t.*,
    c.code AS code_carte_type,
    tc.nom AS nom_carte
FROM tir t
LEFT JOIN carte c ON c.id_carte = t.id_carte
LEFT JOIN type_carte tc ON tc.code = c.code
WHERE t.id_partie = %s
ORDER BY t.num_tour, t.num_tir;

-- Mise à jour de l’état d’un navire
UPDATE navire SET etat = %s WHERE id_navire = %s;

-- Recherche de la flottille d’un joueur pour une partie
SELECT id_flotille FROM flotille WHERE id_partie = %s AND id_joueur = %s;

-- Création d’un nouvel identifiant de flottille
SELECT COALESCE(MAX(id_flotille), 0) + 1 FROM flotille;

-- Création d’une flottille
INSERT INTO flotille (id_flotille, pavillon, nb_navires, id_joueur, id_partie)
VALUES (%s, %s, %s, %s, %s);

-- Création d’un nouvel identifiant de navire
SELECT COALESCE(MAX(id_navire), 0) + 1 FROM navire;

-- Placement d’un navire
INSERT INTO navire (id_navire, type, x, y, sens, etat, id_flotille)
VALUES (%s, %s, %s, %s, %s, %s, %s);

-- Vérification de l’existence d’un tour
SELECT 1 FROM tour WHERE id_partie = %s AND num_tour = %s;

-- Création d’un tour
INSERT INTO tour (
    num_tour,
    id_partie,
    joueur_navires_coules,
    joueur_navires_touches,
    joueur_cases_a_explorer,
    adversaire_navires_coules,
    adversaire_navires_touches,
    adversaire_cases_a_explorer
)
VALUES (%s, %s, 0, 0, 100, 0, 0, 100);

-- Vérification qu’une séquence temporelle est ouverte
SELECT 1
FROM sequence_temporelle
WHERE id_partie = %s
  AND date_fin IS NULL
  AND heure_fin IS NULL;

-- Ouverture d’une nouvelle séquence temporelle
INSERT INTO sequence_temporelle (date_debut, heure_debut, date_fin, heure_fin, id_partie)
VALUES (
    CURRENT_DATE,
    CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER),
    NULL,
    NULL,
    %s
);

-- Fermeture de la séquence temporelle ouverte
UPDATE sequence_temporelle
SET
    date_fin = CURRENT_DATE,
    heure_fin = CAST(TO_CHAR(CURRENT_TIMESTAMP, 'HH24MI') AS INTEGER)
WHERE id_partie = %s
  AND date_fin IS NULL
  AND heure_fin IS NULL;

-- Déplacement d’un navire pour la carte Même pas mal
UPDATE navire
SET x = %s, y = %s, sens = %s, etat = 'intact'
WHERE id_navire = %s;

-- Passage d’une partie à l’état en cours
UPDATE partie SET etat = 'en cours' WHERE id_partie = %s;

-- Tirage de la prochaine carte disponible
SELECT
    a.id_carte,
    c.code,
    tc.nom,
    tc.description,
    tc.image
FROM appartient a
JOIN carte c ON c.id_carte = a.id_carte
JOIN type_carte tc ON tc.code = c.code
WHERE a.id_pioche = %s
  AND a.etat = 'disponible'
ORDER BY a.rang
LIMIT 1;

-- Passage d’une carte à l’état utilisée
UPDATE appartient SET etat = 'utilisee' WHERE id_pioche = %s AND id_carte = %s;

-- Création d’un numéro de tir dans un tour
SELECT COALESCE(MAX(num_tir), 0) + 1 FROM tir WHERE id_partie = %s AND num_tour = %s;

-- Chargement d’une carte à partir de son identifiant
SELECT c.id_carte, c.code, tc.nom, tc.description, tc.image
FROM carte c
JOIN type_carte tc ON tc.code = c.code
WHERE c.id_carte = %s;

-- Enregistrement d’un tir
INSERT INTO tir (num_tir, num_tour, id_partie, id_carte, id_joueur, x, y)
VALUES (%s, %s, %s, %s, %s, %s, %s);

-- Mise à jour des statistiques du tour courant
UPDATE tour
SET
    joueur_navires_coules = %s,
    joueur_navires_touches = %s,
    joueur_cases_a_explorer = %s,
    adversaire_navires_coules = %s,
    adversaire_navires_touches = %s,
    adversaire_cases_a_explorer = %s
WHERE id_partie = %s
  AND num_tour = %s;

-- Calcul du nombre total de tirs d’une partie
SELECT COUNT(*) FROM tir WHERE id_partie = %s AND x IS NOT NULL AND y IS NOT NULL;

-- Fin d’une partie avec stockage du gagnant et du score
UPDATE partie
SET etat = %s, score_final = %s, id_gagnant = %s
WHERE id_partie = %s;

-- Suspension d’une partie
UPDATE partie SET etat = 'suspendue' WHERE id_partie = %s;

-- Classement individuel des joueurs humains
SELECT
    j.pseudo,
    j.id_joueur,
    COALESCE(SUM(p.score_final), 0) AS score_total,
    COUNT(DISTINCT p.id_partie) AS nb_parties
FROM humain h
JOIN joueur j ON h.id_joueur = j.id_joueur
LEFT JOIN partie p
    ON p.id_humain = h.id_joueur
   AND p.score_final IS NOT NULL
GROUP BY j.id_joueur, j.pseudo
ORDER BY score_total DESC, nb_parties DESC;

-- Classement individuel des joueurs humains avec filtre temporel
SELECT
    j.pseudo,
    j.id_joueur,
    COALESCE(SUM(p.score_final), 0) AS score_total,
    COUNT(DISTINCT p.id_partie) AS nb_parties
FROM humain h
JOIN joueur j ON h.id_joueur = j.id_joueur
LEFT JOIN partie p
    ON p.id_humain = h.id_joueur
   AND p.score_final IS NOT NULL
LEFT JOIN sequence_temporelle st
    ON st.id_partie = p.id_partie
   AND st.date_debut >= CURRENT_DATE - make_interval(months => %s)
GROUP BY j.id_joueur, j.pseudo
ORDER BY score_total DESC, nb_parties DESC;

-- Classement par pavillon
SELECT
    f.pavillon,
    COALESCE(SUM(p.score_final), 0) AS score_total,
    COUNT(DISTINCT p.id_partie) AS nb_parties,
    COUNT(DISTINCT p.id_humain) AS nb_joueurs
FROM flotille f
JOIN partie p
    ON p.id_partie = f.id_partie
   AND p.score_final IS NOT NULL
JOIN humain h
    ON h.id_joueur = p.id_humain
WHERE LOWER(TRIM(f.pavillon)) != 'coalition'
GROUP BY f.pavillon
ORDER BY score_total DESC, nb_parties DESC;

-- Classement par pavillon avec filtre temporel
SELECT
    f.pavillon,
    COALESCE(SUM(p.score_final), 0) AS score_total,
    COUNT(DISTINCT p.id_partie) AS nb_parties,
    COUNT(DISTINCT p.id_humain) AS nb_joueurs
FROM flotille f
JOIN partie p
    ON p.id_partie = f.id_partie
   AND p.score_final IS NOT NULL
JOIN humain h
    ON h.id_joueur = p.id_humain
LEFT JOIN sequence_temporelle st
    ON st.id_partie = p.id_partie
   AND st.date_debut >= CURRENT_DATE - make_interval(months => %s)
WHERE LOWER(TRIM(f.pavillon)) != 'coalition'
GROUP BY f.pavillon
ORDER BY score_total DESC, nb_parties DESC;
