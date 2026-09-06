import unittest
from tools.performance_probe import summarize_frames, increasing

class PerformanceScenarioTests(unittest.TestCase):
    def test_percentile_uses_worst_frame_tail(self):
        report=summarize_frames([1/60]*980+[1/30]*20)
        self.assertAlmostEqual(report['p1_fps'],30)
        self.assertFalse(report['passes'])

    def test_two_long_frames_and_monotonic_growth_fail(self):
        self.assertTrue(summarize_frames([.3,.3]+[1/60]*1000)['persistent_stall_indices'])
        self.assertFalse(summarize_frames([1/60]*1000)['persistent_stall_indices'])
        self.assertTrue(increasing([{'n':1},{'n':1},{'n':3}],'n'))
        self.assertFalse(increasing([{'n':2},{'n':1},{'n':3}],'n'))
        self.assertFalse(increasing([{'n':1},{'n':1}],'n'))
