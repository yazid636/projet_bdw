CREATE TABLE TYPE_CARTE (
  code        int ,
  bonus       VARCHAR(42),
  nom         VARCHAR(42),
  description VARCHAR(42),
  image       VARCHAR(42),
  PRIMARY KEY (code)
);

CREATE TABLE RANG_CARTE (
  rang int,
  PRIMARY KEY (rang)
);

CREATE TABLE PIOCHE (
  id_pioche       int,
  nom_distrib VARCHAR(42),
  PRIMARY KEY (id_pioche)
);

CREATE TABLE JOUEUR (
  id_joueur int,
  pseudo VARCHAR(50),
  PRIMARY KEY (id_joueur)
);

CREATE TABLE HUMAIN (
  id_joueur              int,
  nom               VARCHAR(42),
  prenom            VARCHAR(42),
  date_de_naissance DATE,
  date_de_creation  DATE,
  PRIMARY KEY (id_joueur),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur)
);

CREATE TABLE VIRTUEL (
  id_joueur          int,
  niveau        VARCHAR(42),
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
  etat        VARCHAR(42),
  score_final int,
  id_humain        int,
  id_virtuel        int,
  id_pioche int,
  id_gagnant int,
  PRIMARY KEY (id_partie),
  FOREIGN KEY (id_humain) REFERENCES HUMAIN(id_joueur),
  FOREIGN KEY (id_virtuel) REFERENCES VIRTUEL(id_joueur),
  FOREIGN KEY (id_pioche) REFERENCES PIOCHE(id_pioche),
  FOREIGN KEY (id_gagnant) REFERENCES JOUEUR(id_joueur)
);

CREATE TABLE TOUR (
  num_tour  int ,
  id_partie int,
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
  pavillon   VARCHAR(42),
  nb_navires int,
  id_joueur       int,
  id_partie      int,
  PRIMARY KEY (id_flotille),
  FOREIGN KEY (id_joueur) REFERENCES JOUEUR(id_joueur),
  FOREIGN KEY (id_partie) REFERENCES PARTIE(id_partie)
);

CREATE TABLE NAVIRE (
  id_navire   int ,
  type VARCHAR(42),
  x    int,
  y    int,
  sens VARCHAR(42),
  etat VARCHAR(42),
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