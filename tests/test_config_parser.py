import os
import sys
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from synthflow.core.config_parser import ConfigParser


class ConfigParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = ConfigParser()
        self.config_dir = os.path.join(os.path.dirname(__file__), "..", "config")

    def test_load_sample_process(self):
        path = os.path.join(self.config_dir, "sample_process.yaml")
        model = self.parser.load_config(path)
        self.assertEqual(model.name, "SearchProcess")
        self.assertGreaterEqual(len(model.steps), 4)

    def test_load_sample_approval(self):
        path = os.path.join(self.config_dir, "sample_approval.yaml")
        model = self.parser.load_config(path)
        self.assertEqual(model.name, "ApprovalProcess")
        self.assertGreaterEqual(len(model.steps), 3)


if __name__ == "__main__":
    unittest.main()

