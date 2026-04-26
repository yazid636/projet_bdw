CREATE TABLE TYPE_CARTE (
  code        int ,
  bonus       VARCHAR(10),
  nom         VARCHAR(80),
  description VARCHAR(255),
  image       VARCHAR(100),
  PRIMARY KEY (code)
);

CREATE TABLE RANG_CARTE (
  rang int,
  PRIMARY KEY (rang)
);

CREATE TABLE PIOCHE (
  id_pioche       int,
  nom_distrib VARCHAR(80),
  PRIMARY KEY (id_pioche)
);

CREATE TABLE JOUEUR (
  id_joueur int,
  pseudo VARCHAR(80),
  PRIMARY KEY (id_joueur)
);

CREATE TABLE HUMAIN (
  id_joueur              int,
  nom               VARCHAR(80),
  prenom            VARCHAR(80),
  date_de_naissance DATE,
  date_de_creation  DATE,
  PRIMARY KEY (id_joueur),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur)
);

CREATE TABLE VIRTUEL (
  id_joueur          int,
  niveau        VARCHAR(30),
  date_creation DATE,
  id_createur int,
  PRIMARY KEY (id_joueur),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur),
  FOREIGN KEY (id_createur) REFERENCES HUMAIN(id_joueur)
);

CREATE TABLE CARTE (
  id_carte int,
  code int,
  PRIMARY KEY (id_carte),
  FOREIGN KEY (code) REFERENCES TYPE_CARTE(code)
);

CREATE TABLE APPARTIENT (
  id_carte  int,
  rang  int,
  id_pioche int,
  etat  VARCHAR(50),
  PRIMARY KEY (id_carte, rang, id_pioche),
  FOREIGN KEY (id_carte) REFERENCES CARTE(id_carte),
  FOREIGN KEY (rang) REFERENCES RANG_CARTE(rang),
  FOREIGN KEY (id_pioche) REFERENCES PIOCHE(id_pioche)
);

CREATE TABLE A_POUR_DISTRIBUTION (
  id_pioche       int,
  code      int,
  pourcentage     int,
  PRIMARY KEY (id_pioche, code),
  FOREIGN KEY (id_pioche) REFERENCES PIOCHE(id_pioche),
  FOREIGN KEY (code) REFERENCES TYPE_CARTE(code)
);

CREATE TABLE PARTIE (
  id_partie        int,
  etat        VARCHAR(30),
  score_final int,
  id_humain        int,
  id_virtuel        int,
  id_pioche int,
  id_gagnant int,
  etat_jeu TEXT,
  PRIMARY KEY (id_partie),
  FOREIGN KEY (id_humain) REFERENCES HUMAIN(id_joueur),
  FOREIGN KEY (id_virtuel) REFERENCES VIRTUEL(id_joueur),
  FOREIGN KEY (id_pioche) REFERENCES PIOCHE(id_pioche),
  FOREIGN KEY (id_gagnant) REFERENCES JOUEUR(id_joueur)
);

CREATE TABLE TOUR (
  num_tour  int ,
  id_partie int,
  joueur_navires_coules int DEFAULT 0,
  joueur_navires_touches int DEFAULT 0,
  joueur_cases_a_explorer int DEFAULT 100,
  adversaire_navires_coules int DEFAULT 0,
  adversaire_navires_touches int DEFAULT 0,
  adversaire_cases_a_explorer int DEFAULT 100,
  PRIMARY KEY (num_tour, id_partie),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);

CREATE TABLE TIR (
  num_tir   int,
  num_tour int,
  id_partie int,
  id_carte int,
  id_joueur int,
  x     int,
  y     int,
  PRIMARY KEY (num_tir, num_tour, id_partie),
  FOREIGN KEY (num_tour, id_partie) REFERENCES TOUR(num_tour, id_partie),
  FOREIGN KEY (id_carte) REFERENCES CARTE(id_carte),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur)
);

CREATE TABLE FLOTILLE (
  id_flotille         int,
  pavillon   VARCHAR(80),
  nb_navires int,
  id_joueur       int,
  id_partie      int,
  PRIMARY KEY (id_flotille),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);

CREATE TABLE NAVIRE (
  id_navire   int ,
  type VARCHAR(80),
  x    int,
  y    int,
  sens VARCHAR(10),
  etat VARCHAR(20),
  id_flotille int,
  PRIMARY KEY (id_navire),
  FOREIGN KEY (id_flotille) REFERENCES FLOTILLE(id_flotille)
);

CREATE TABLE LEURRE (
  id_leurre   int,
  x    int,
  y    int,
  id_partie int,
  PRIMARY KEY (id_leurre),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);

CREATE TABLE SAUVER_WILLY (
  id_sw   int ,
  x    int,
  y    int,
  id_partie int,
  PRIMARY KEY (id_sw),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);

CREATE TABLE SEQUENCE_TEMPORELLE (
  date_debut  DATE,
  heure_debut int,
  date_fin    DATE,
  heure_fin   int,
  id_partie   int,
  PRIMARY KEY (date_debut, heure_debut, id_partie),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);


---------------------------------------------------------------------


INSERT INTO JOUEUR (id_joueur, pseudo) VALUES
  (1, 'Yacou'),
  (2, 'Zelda'),
  (3, 'Mario'),
  (4, 'You'),
  (5, 'Kirby'),
  (6, 'Pikachu'),
  (7, 'JD'),
  (8, 'evaB'),
  (9, 'LaRo'),
  (10, 'Thanos'),
  (11, 'ET');

INSERT INTO HUMAIN (id_joueur, nom, prenom, date_de_naissance, date_de_creation) VALUES
  (1, 'ACOULAY', 'Yves', '2001-02-04', '2026-03-01'),
  (4, 'AITORPILLET', 'Youssef', '2002-12-23', '2026-03-01'),
  (7, 'DEAU', 'John', '1999-11-02', '2026-03-01'),
  (8, 'BOMBARDER', 'Eva', '1999-11-02', '2026-03-01'),
  (9, 'ROQUETTE', 'Lance', '1998-10-07', '2026-03-01'),
  (11, 'TOUCOULET', 'Ella', '2005-08-14', '2026-03-01');

INSERT INTO VIRTUEL (id_joueur, niveau, date_creation, id_createur) VALUES
  (2, 'expert', '2026-03-03', 1),
  (3, 'faible', '2026-03-04', 4),
  (5, 'faible', '2026-03-06', 4),
  (6, 'intermediaire', '2026-03-07', 7),
  (10, 'expert', '2026-03-11', 11);

INSERT INTO TYPE_CARTE (code, bonus, nom, description, image) VALUES
  (1, NULL, 'Missile', 'Tir classique sur une case', 'carte1.png'),
  (2, 'true', 'Rejoue une fois', 'Permet de jouer une seconde fois', 'carte2.png'),
  (3, 'true', 'Vide ou pas vide ?', 'Indique si une case est vide avant le tir', 'carte3.png'),
  (4, 'true', 'Meme pas mal', 'Annule un degat subi sur un navire', 'carte4.png'),
  (5, 'true', 'Bateau leurre', 'Place un bateau leurre sur la grille', 'carte5.png'),
  (6, 'true', 'Sauver Willy', 'Place une orque sur la grille', 'carte6.png'),
  (7, 'true', 'Mega-bombe', 'Touche la case cible et les 8 cases adjacentes', 'carte7.png'),
  (8, 'true', 'Etoile de la mort', 'Touche une zone de 25 cases', 'carte8.png'),
  (9, NULL, 'Passe ton tour', 'Le joueur perd son tour', 'carte9.png'),
  (10, NULL, 'Oups', 'Un de vos navires est touche a la place', 'carte10.png');

INSERT INTO PIOCHE (id_pioche, nom_distrib) VALUES
  (103, 'Distribution 103'),
  (105, 'Distribution 105');

INSERT INTO A_POUR_DISTRIBUTION (id_pioche, code, pourcentage) VALUES
  (103, 1, 10),
  (103, 2, 5),
  (103, 3, 15),
  (103, 4, 10),
  (103, 5, 10),
  (103, 6, 10),
  (103, 7, 10),
  (103, 8, 5),
  (103, 9, 5),
  (103, 10, 20),
  (105, 1, 50),
  (105, 2, 10),
  (105, 3, 10),
  (105, 4, 5),
  (105, 5, 3),
  (105, 6, 3),
  (105, 7, 3),
  (105, 8, 1),
  (105, 9, 10),
  (105, 10, 5);

INSERT INTO RANG_CARTE (rang)
SELECT gs
FROM generate_series(1, 100) AS gs;

INSERT INTO CARTE (id_carte, code)
SELECT
  gs,
  CASE
    WHEN gs BETWEEN 1 AND 50 THEN 1
    WHEN gs BETWEEN 51 AND 60 THEN 2
    WHEN gs BETWEEN 61 AND 70 THEN 3
    WHEN gs BETWEEN 71 AND 75 THEN 4
    WHEN gs BETWEEN 76 AND 78 THEN 5
    WHEN gs BETWEEN 79 AND 81 THEN 6
    WHEN gs BETWEEN 82 AND 84 THEN 7
    WHEN gs = 85 THEN 8
    WHEN gs BETWEEN 86 AND 95 THEN 9
    ELSE 10
  END
FROM generate_series(1, 100) AS gs;

INSERT INTO CARTE (id_carte, code)
SELECT
  gs,
  CASE
    WHEN gs BETWEEN 101 AND 110 THEN 1
    WHEN gs BETWEEN 111 AND 115 THEN 2
    WHEN gs BETWEEN 116 AND 130 THEN 3
    WHEN gs BETWEEN 131 AND 140 THEN 4
    WHEN gs BETWEEN 141 AND 150 THEN 5
    WHEN gs BETWEEN 151 AND 160 THEN 6
    WHEN gs BETWEEN 161 AND 170 THEN 7
    WHEN gs BETWEEN 171 AND 175 THEN 8
    WHEN gs BETWEEN 176 AND 180 THEN 9
    ELSE 10
  END
FROM generate_series(101, 200) AS gs;

INSERT INTO APPARTIENT (id_carte, rang, id_pioche, etat)
SELECT gs, gs, 105, 'disponible'
FROM generate_series(1, 100) AS gs;

INSERT INTO APPARTIENT (id_carte, rang, id_pioche, etat)
SELECT gs, gs - 100, 103, 'disponible'
FROM generate_series(101, 200) AS gs;

INSERT INTO PARTIE (id_partie, etat, score_final, id_humain, id_virtuel, id_pioche, id_gagnant) VALUES
  (41, 'terminee', 140, 1, 2, 103, 1),
  (52, 'en cours', NULL, 1, 3, 105, NULL),
  (63, 'suspendue', NULL, 4, 3, 103, NULL);

INSERT INTO SEQUENCE_TEMPORELLE (date_debut, heure_debut, date_fin, heure_fin, id_partie) VALUES
  ('2026-03-04', 1005, '2026-03-04', 1035, 41),
  ('2026-03-04', 1400, '2026-03-04', 1532, 41),
  ('2026-03-13', 915, NULL, NULL, 52),
  ('2026-03-10', 1805, '2026-03-10', 1905, 63);

INSERT INTO TOUR (num_tour, id_partie) VALUES
  (1, 41),
  (2, 41),
  (3, 41),
  (1, 52),
  (2, 52),
  (1, 63);

INSERT INTO FLOTILLE (id_flotille, pavillon, nb_navires, id_joueur, id_partie) VALUES
  (1, 'France', 5, 1, 41),
  (2, 'Hyrule', 5, 2, 41),
  (3, 'France', 5, 1, 52),
  (4, 'Mushroom', 5, 3, 52),
  (5, 'France', 5, 4, 63),
  (6, 'Mushroom', 5, 3, 63);

INSERT INTO NAVIRE (id_navire, type, x, y, sens, etat, id_flotille) VALUES
  (1, 'torpilleur', 2, 2, 'V', 'coule', 1),
  (2, 'porte-avion', 4, 3, 'H', 'intact', 1),
  (3, 'contre-torpilleur', 8, 4, 'H', 'intact', 1),
  (4, 'contre-torpilleur', 9, 6, 'H', 'intact', 1),
  (5, 'croiseur', 1, 7, 'V', 'touche', 1),
  (6, 'torpilleur', 3, 3, 'V', 'touche', 2),
  (7, 'porte-avion', 5, 4, 'H', 'coule', 2),
  (8, 'contre-torpilleur', 7, 5, 'H', 'intact', 2),
  (9, 'contre-torpilleur', 8, 6, 'H', 'intact', 2),
  (10, 'croiseur', 2, 9, 'V', 'intact', 2),
  (11, 'torpilleur', 2, 2, 'V', 'intact', 3),
  (12, 'porte-avion', 4, 3, 'H', 'touche', 3),
  (13, 'contre-torpilleur', 8, 4, 'H', 'intact', 3),
  (14, 'contre-torpilleur', 9, 6, 'H', 'intact', 3),
  (15, 'croiseur', 1, 7, 'V', 'intact', 3),
  (16, 'torpilleur', 3, 3, 'V', 'coule', 4),
  (17, 'porte-avion', 5, 4, 'H', 'touche', 4),
  (18, 'contre-torpilleur', 7, 5, 'H', 'intact', 4),
  (19, 'contre-torpilleur', 8, 6, 'H', 'intact', 4),
  (20, 'croiseur', 2, 9, 'V', 'intact', 4),
  (21, 'torpilleur', 2, 2, 'V', 'intact', 5),
  (22, 'porte-avion', 4, 3, 'H', 'intact', 5),
  (23, 'contre-torpilleur', 8, 4, 'H', 'touche', 5),
  (24, 'contre-torpilleur', 9, 6, 'H', 'intact', 5),
  (25, 'croiseur', 1, 7, 'V', 'intact', 5),
  (26, 'torpilleur', 3, 3, 'V', 'intact', 6),
  (27, 'porte-avion', 5, 4, 'H', 'intact', 6),
  (28, 'contre-torpilleur', 7, 5, 'H', 'intact', 6),
  (29, 'contre-torpilleur', 8, 6, 'H', 'intact', 6),
  (30, 'croiseur', 2, 9, 'V', 'coule', 6);

INSERT INTO TIR (num_tir, num_tour, id_partie, id_carte, id_joueur, x, y) VALUES
  (1, 1, 41, 12, 1, 3, 3),
  (2, 1, 41, 24, 2, 6, 1),
  (1, 2, 41, 10, 1, 3, 3),
  (2, 2, 41, 66, 2, NULL, NULL),
  (1, 3, 41, 6, 1, 3, 4),
  (2, 3, 41, 16, 2, 7, 5),
  (1, 1, 52, 6, 1, 1, 1),
  (2, 1, 52, 14, 3, 5, 4),
  (3, 1, 52, 25, 3, 6, 4),
  (1, 2, 52, 11, 1, 8, 2),
  (2, 2, 52, 60, 3, 8, 2),
  (1, 1, 63, 18, 4, 4, 6),
  (2, 1, 63, 50, 3, 6, 3);


UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte1.png' WHERE code = 1;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte2.png' WHERE code = 2;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte3.png' WHERE code = 3;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte4.png' WHERE code = 4;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte5.png' WHERE code = 5;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte6.png' WHERE code = 6;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte7.png' WHERE code = 7;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte8.png' WHERE code = 8;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte9.png' WHERE code = 9;
UPDATE TYPE_CARTE SET image = '/bataille_navale/static/img/carte10.png' WHERE code = 10;
