import unittest
from coordinator.test import CoordinatorTestCase

suite = unittest.TestSuite()
runner = unittest.TextTestRunner()

suite.addTest(CoordinatorCanvasTest("testMapToolChange"))
runner.run(suite)