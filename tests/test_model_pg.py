import sys
import unittest
from pathlib import Path
from random import seed

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bataille_navale"))

from model.model_pg import (
    NAVIRES_A_PLACER,
    TAILLE_NAVIRES,
    attack_cells_from_code,
    build_action_messages,
    build_attack_message,
    build_exploration_maps,
    build_final_message,
    can_place_shape,
    cell_in_grid,
    cells_from_navire,
    coord_to_label,
    decoy_is_still_hidden_for_attacker,
    default_game_state,
    format_grid_for_template,
    get_player_opponent,
    get_ship_cell_owner_map,
    get_special_cells,
    grid_value_for_template,
    load_game_state,
    normalize_card_image_path,
    parse_coordonnee,
    random_ship_positions,
    serialize_card,
)


class TestModelPg(unittest.TestCase):
    def test_parse_coordonnee(self):
        self.assertEqual(parse_coordonnee("A1"), (1, 1))
        self.assertEqual(parse_coordonnee(" j10 "), (10, 10))
        self.assertIsNone(parse_coordonnee("K1"))
        self.assertIsNone(parse_coordonnee("A0"))
        self.assertIsNone(parse_coordonnee("AA"))
        self.assertIsNone(parse_coordonnee(None))

    def test_coord_to_label(self):
        self.assertEqual(coord_to_label(1, 1), "A1")
        self.assertEqual(coord_to_label(10, 10), "J10")
        self.assertEqual(coord_to_label(0, 1), "")

    def test_cell_in_grid(self):
        self.assertTrue(cell_in_grid(1, 1))
        self.assertTrue(cell_in_grid(10, 10))
        self.assertFalse(cell_in_grid(11, 1))
        self.assertFalse(cell_in_grid(1, 0))

    def test_cells_from_navire(self):
        navire = {"type": "torpilleur", "x": 2, "y": 3, "sens": "H"}
        self.assertEqual(cells_from_navire(navire), [(2, 3), (3, 3)])
        navire = {"type": "croiseur", "x": 4, "y": 6, "sens": "V"}
        self.assertEqual(cells_from_navire(navire), [(4, 6), (4, 7), (4, 8), (4, 9)])

    def test_attack_cells_from_code(self):
        self.assertEqual(attack_cells_from_code(1, 5, 5), [(5, 5)])
        self.assertEqual(attack_cells_from_code(2, 5, 5), [(5, 5)])
        self.assertEqual(attack_cells_from_code(3, 5, 5), [(5, 5)])
        self.assertEqual(len(attack_cells_from_code(7, 5, 5)), 9)
        self.assertEqual(len(attack_cells_from_code(8, 5, 5)), 25)
        self.assertEqual(len(attack_cells_from_code(7, 1, 1)), 4)
        self.assertEqual(len(attack_cells_from_code(8, 1, 1)), 9)
        self.assertEqual(attack_cells_from_code(9, 5, 5), [])
        self.assertEqual(attack_cells_from_code(10, 5, 5), [])
        self.assertEqual(attack_cells_from_code(1, None, 5), [])

    def test_default_and_loaded_game_state(self):
        state = default_game_state()
        self.assertEqual(state["phase"], "creation")
        self.assertEqual(state["tour_courant"], 0)
        self.assertEqual(state["ia_cibles"], [])

        loaded = load_game_state('{"phase": "tir_joueur", "ia_cibles": null}')
        self.assertEqual(loaded["phase"], "tir_joueur")
        self.assertEqual(loaded["ia_cibles"], [])
        self.assertEqual(loaded["leurres"], [])

        invalid = load_game_state("pas du json")
        self.assertEqual(invalid["phase"], "creation")

    def test_can_place_shape(self):
        self.assertTrue(can_place_shape([(1, 1), (2, 1)], occupied=set(), blocked=set()))
        self.assertFalse(can_place_shape([(1, 1), (11, 1)], occupied=set(), blocked=set()))
        self.assertFalse(can_place_shape([(1, 1)], occupied={(1, 1)}, blocked=set()))
        self.assertFalse(can_place_shape([(1, 1)], occupied=set(), blocked={(1, 1)}))

    def test_random_ship_positions_are_valid(self):
        seed(42)
        navires = random_ship_positions()
        self.assertEqual(len(navires), len(NAVIRES_A_PLACER))
        self.assertCountEqual([navire["type"] for navire in navires], NAVIRES_A_PLACER)

        occupied = set()
        for navire in navires:
            cellules = cells_from_navire(navire)
            self.assertEqual(len(cellules), TAILLE_NAVIRES[navire["type"]])
            for cellule in cellules:
                self.assertTrue(cell_in_grid(*cellule))
                self.assertNotIn(cellule, occupied)
                occupied.add(cellule)

    def test_special_cells(self):
        state = {
            "leurres": [
                {"owner": 1, "cells": [[1, 1], [2, 1]], "actif": True},
                {"owner": 1, "cells": [[4, 4]], "actif": False},
                {"owner": 2, "cells": [[5, 5]], "actif": True},
            ],
            "willys": [
                {"owner": 1, "x": 3, "y": 3, "actif": True},
                {"owner": 2, "x": 6, "y": 6, "actif": True},
            ],
        }
        leurres, willys = get_special_cells(state, 1)
        self.assertEqual(leurres, {(1, 1), (2, 1)})
        self.assertEqual(willys, {(3, 3)})

    def test_player_opponent(self):
        partie = {"id_humain": 1, "id_virtuel": 2}
        self.assertEqual(get_player_opponent(partie, 1), 2)
        self.assertEqual(get_player_opponent(partie, 2), 1)

    def test_build_exploration_maps(self):
        partie = {"id_humain": 1, "id_virtuel": 2}
        tirs = [
            {"code_carte_type": 1, "id_joueur": 1, "x": 1, "y": 1},
            {"code_carte_type": 7, "id_joueur": 2, "x": 5, "y": 5},
            {"code_carte_type": 9, "id_joueur": 1, "x": None, "y": None},
            {"code_carte_type": 10, "id_joueur": 2, "x": 2, "y": 2},
        ]

        explorees_sur_grille, explorees_par_joueur = build_exploration_maps(partie, tirs)

        self.assertIn((1, 1), explorees_sur_grille[2])
        self.assertIn((1, 1), explorees_par_joueur[1])
        self.assertIn((5, 5), explorees_sur_grille[1])
        self.assertNotIn((2, 2), explorees_sur_grille[2])
        self.assertNotIn((2, 2), explorees_par_joueur[2])

    def test_ship_cell_owner_map(self):
        navires = [
            {"id_navire": 1, "type": "torpilleur", "x": 1, "y": 1, "sens": "H"},
            {"id_navire": 2, "type": "croiseur", "x": 4, "y": 4, "sens": "V"},
        ]
        mapping = get_ship_cell_owner_map(navires)
        self.assertEqual(mapping[(1, 1)]["id_navire"], 1)
        self.assertEqual(mapping[(2, 1)]["id_navire"], 1)
        self.assertEqual(mapping[(4, 7)]["id_navire"], 2)

    def test_attack_messages(self):
        resume = {
            "impacts": [
                {"coordonnee": "A1", "resultat": "touche"},
                {"coordonnee": "B1", "resultat": "eau"},
            ],
            "navires_coules": ["torpilleur"],
        }
        message = build_attack_message(resume)
        self.assertIn("Touches en A1", message)
        self.assertIn("A l'eau en B1", message)
        self.assertIn("torpilleur", message)
        self.assertEqual(build_attack_message({"impacts": [], "navires_coules": []}), "Aucun impact.")

    def test_card_serialization(self):
        carte = {
            "id_carte": 12,
            "code": 8,
            "nom": "Etoile de la mort",
            "description": "Touche une zone de 25 cases",
            "image": "carte8.png",
        }
        serialized = serialize_card(carte)
        self.assertEqual(serialized["code_nom"], "C_ETOILE")
        self.assertEqual(serialized["image"], "/bataille_navale/static/img/carte8.png")
        self.assertIsNone(serialize_card(None))
        self.assertEqual(
            normalize_card_image_path("/bataille_navale/static/img/carte1.png"),
            "/bataille_navale/static/img/carte1.png",
        )

    def test_decoy_visibility(self):
        leurre = {"hit_cell": [5, 5]}
        self.assertTrue(decoy_is_still_hidden_for_attacker(leurre, {(4, 5), (6, 5)}))
        self.assertFalse(decoy_is_still_hidden_for_attacker(leurre, {(4, 5), (6, 5), (5, 4), (5, 6)}))
        self.assertFalse(decoy_is_still_hidden_for_attacker({"hit_cell": None}, set()))

    def test_format_grid_for_template(self):
        grid = {
            (x, y): {"label": "", "classes": ["cell-mer"]}
            for x in range(1, 11)
            for y in range(1, 11)
        }
        formatted = format_grid_for_template(grid)
        self.assertEqual(formatted["colonnes"][0], "A")
        self.assertEqual(len(formatted["lignes"]), 10)
        self.assertEqual(len(formatted["lignes"][0]["cellules"]), 10)
        self.assertIn("grille-case", formatted["lignes"][0]["cellules"][0]["classes"])

    def test_final_and_action_messages(self):
        self.assertIsNone(build_final_message({"id_gagnant": None}))
        self.assertEqual(
            build_final_message({"id_gagnant": 1, "id_humain": 1, "pseudo_humain": "Yacou"}),
            "Yacou a gagne.",
        )
        self.assertEqual(
            build_final_message({"id_gagnant": 2, "id_humain": 1, "pseudo_humain": "Yacou"}),
            "Yacou a perdu.",
        )
        self.assertEqual(build_action_messages({"message": "Touche"}), ["Touche"])
        self.assertEqual(
            build_action_messages({"actions": [{"message": "A"}, {"message": ""}, {"message": "B"}]}),
            ["A", "B"],
        )

    def test_grid_value_for_template(self):
        self.assertEqual(grid_value_for_template("navire"), "N")
        self.assertEqual(grid_value_for_template("touche"), "X")
        self.assertEqual(grid_value_for_template("eau"), "o")
        self.assertEqual(grid_value_for_template("inconnu"), "")
        self.assertEqual(grid_value_for_template("type_inconnu"), "")


if __name__ == "__main__":
    unittest.main()
