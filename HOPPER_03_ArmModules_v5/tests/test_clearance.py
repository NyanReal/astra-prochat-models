import unittest,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class Clearance(unittest.TestCase):
 def test_load_members_do_not_pierce_shells(self):
  report=json.loads((R/'docs/clearance_report.json').read_text())
  self.assertEqual(report['arm_frames_to_shell_contacts'],[])
 def test_arms_clear_original_body(self):
  report=json.loads((R/'docs/clearance_report.json').read_text())
  self.assertEqual(report['arms_to_base_rest_contacts'],[])
 def test_dampers_do_not_pierce_shells(self):
  report=json.loads((R/'docs/clearance_report.json').read_text())
  self.assertEqual(report['arm_damper_to_armor_contacts'],[])
 def test_original_cockpit_clears_modules(self):
  report=json.loads((R/'docs/clearance_report.json').read_text())
  self.assertEqual(report['cockpit_samples'],181);self.assertEqual(report['arms_to_moving_cockpit_contacts'],[])
