CREATE TABLE APPARTIENT (
  PRIMARY KEY (id_carte, rang, id_pioche),
  id_carte  int,
  rang  int,
  id_pioche int,
  etat  VARCHAR(42)
);

CREATE TABLE A_POUR_DISTRIBUTION (
  PRIMARY KEY (id_pioche, code),
  id_pioche       int,
  code      int,
  pourcentage     int,
);

CREATE TABLE CARTE (
  PRIMARY KEY (id_carte),
  id_carte int,
  code int,
);

CREATE TABLE FLOTILLE (
  PRIMARY KEY (id_flotille),
  id_flotille         int,
  pavillon   VARCHAR(42),
  nb_navires int,
  id_joueur       int,
  id_partie      int,
);

CREATE TABLE HUMAIN (
  PRIMARY KEY (id_humain),
  id_humain              int,
  nom               VARCHAR(42),
  prenom            VARCHAR(42),
  date_de_naissance DATE,
  date_de_creation  DATE
);

CREATE TABLE VIRTUEL (
  PRIMARY KEY (id_virtuel),
  id_virtuel          int,
  niveau        VARCHAR(42),
  date_creation VARCHAR(42),
);

CREATE TABLE LEURRE (
  PRIMARY KEY (id_leurre),
  id_leurre   int,
  x    int,
  y    int,
  id_partie int
);

CREATE TABLE NAVIRE (
  PRIMARY KEY (id_navire),
  id_navire   int ,
  type VARCHAR(42),
  x    int,
  y    int,
  sens VARCHAR(42),
  etat VARCHAR(42),
  id_flotille VARCHAR(42)
);

CREATE TABLE PARTIE (
  PRIMARY KEY (code),
  id_partie        int,
  etat        VARCHAR(42),
  niveau      VARCHAR(42),
  nom         VARCHAR(42),
  score_final int,
  id_humain        int,
  id_virtuel        int
);

CREATE TABLE PIOCHE (
  PRIMARY KEY (id_pioche),
  id_pioche       int,
  nom_distrib VARCHAR(42)
);

CREATE TABLE SAUVER_WILLY (
  PRIMARY KEY (id_sw),
  id_sw   int ,
  x    int,
  y    int,
  id_partie int
);

CREATE TABLE SEQUENCE_TEMPORELLE (
  date_debut  DATE,
  heure_debut int,
  date_fin    DATE,
  heure_fin   int,
  id_partie   int
);

CREATE TABLE TIR (
  PRIMARY KEY (num_tir, num_tour, id_partie),
  num_tir   int,
  num_tour int,
  id_partie int,
  id_carte int,
  id_joueur int,
  x     int,
  y     int,
);

CREATE TABLE TOUR (
  PRIMARY KEY (num_tour, id_partie),
  num_tour  int ,
  id_partie int
);

CREATE TABLE TYPE_CARTE (
  PRIMARY KEY (code),
  code        VARCHAR(42) ,
  bonus       VARCHAR(42),
  nom         VARCHAR(42),
  description VARCHAR(42),
  image       VARCHAR(42)
);

ALTER TABLE APPARTIENT ADD FOREIGN KEY (id_pioche) REFERENCES PIOCHE (id_pioche);
ALTER TABLE APPARTIENT ADD FOREIGN KEY (id_carte) REFERENCES CARTE (id_carte);

ALTER TABLE A_POUR_DISTRIBUTION ADD FOREIGN KEY (code) REFERENCES TYPE_CARTE (code);
ALTER TABLE A_POUR_DISTRIBUTION ADD FOREIGN KEY (id_pioche) REFERENCES PIOCHE (id_pioche);

ALTER TABLE CARTE ADD FOREIGN KEY (code) REFERENCES TYPE_CARTE (code);

ALTER TABLE FLOTILLE ADD FOREIGN KEY (id_partie) REFERENCES PARTIE (id_partie);

ALTER TABLE LEURRE ADD FOREIGN KEY (id_partie) REFERENCES PARTIE (id_partie);

ALTER TABLE NAVIRE ADD FOREIGN KEY (id_flotille) REFERENCES FLOTILLE (id_flotille);

ALTER TABLE PARTIE ADD FOREIGN KEY (id_pioche) REFERENCES PIOCHE (id_pioche);

ALTER TABLE SAUVER_WILLY ADD FOREIGN KEY (id_partie) REFERENCES PARTIE (id_partie);

ALTER TABLE SEQUENCE_TEMPORELLE ADD FOREIGN KEY (id_partie) REFERENCES PARTIE (id_partie);

ALTER TABLE TIR ADD FOREIGN KEY (id_carte) REFERENCES CARTE (id_carte);
ALTER TABLE TIR ADD FOREIGN KEY (num_2) REFERENCES TOUR (num);

ALTER TABLE TOUR ADD FOREIGN KEY (code) REFERENCES PARTIE (code);

ALTER TABLE VIRTUEL ADD FOREIGN KEY (nom_2) REFERENCES HUMAIN (nom);
ALTER TABLE VIRTUEL ADD FOREIGN KEY (nom_1) REFERENCES HUMAIN (nom);
ALTER TABLE VIRTUEL ADD FOREIGN KEY (id) REFERENCES JOUEUR (id);