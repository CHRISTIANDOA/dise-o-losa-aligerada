import unittest

from src.design import design_slab
from src.models import SlabInputs


class ReferenceCaseTest(unittest.TestCase):
    def setUp(self):
        self.result = design_slab(SlabInputs())

    def test_loads_match_teacher_case(self):
        self.assertAlmostEqual(self.result.selected_height_cm, 17.0, places=6)
        self.assertAlmostEqual(self.result.dead_load_kg_m2, 530.0, places=6)
        self.assertAlmostEqual(self.result.factored_load_kg_m2, 1082.0, places=6)
        self.assertAlmostEqual(self.result.factored_line_load_t_m, 0.4328, places=6)

    def test_moments_match_teacher_case(self):
        values = {item.location: item.mu_tfm for item in self.result.flexure}
        self.assertAlmostEqual(values["Tramo 1"], 0.35410909, places=6)
        self.assertAlmostEqual(values["Tramo 2"], 0.24345, places=6)
        self.assertAlmostEqual(values["Apoyo interior 1"], 0.38952, places=6)

    def test_strength_checks(self):
        self.assertTrue(all(item.status == "CUMPLE" for item in self.result.flexure))
        self.assertEqual(self.result.shear_status, "CUMPLE")
        self.assertAlmostEqual(self.result.temperature_spacing_cm, 25.0, places=6)

    def test_reinforcement_matches_class_selection(self):
        values = {item.location: item.bar_label for item in self.result.flexure}
        self.assertEqual(values["Tramo 1"], '1 Ø 1/2"')
        self.assertEqual(values["Tramo 2"], '1 Ø 3/8"')
        self.assertEqual(values["Apoyo exterior izquierdo"], '1 Ø 3/8"')
        self.assertEqual(values["Apoyo interior 1"], '1 Ø 1/2"')


if __name__ == "__main__":
    unittest.main()
