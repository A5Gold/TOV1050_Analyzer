import pandas as pd
import sys
import os
import unittest

# Adjust path to import backend modules
# Assuming this script is in backend/tests/, we need to add backend/ to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.repeated_finder import RepeatedExceptionFinder

class TestChainLogic(unittest.TestCase):
    def setUp(self):
        self.finder = RepeatedExceptionFinder()

    def create_df(self, id_val, start, end, max_loc, max_val=100, exc_type='TestType'):
        return pd.DataFrame({
            'id': [id_val],
            'exception type': [exc_type],
            'FromM': [start],
            'ToM': [end],
            'maxLocation': [max_loc],
            'maxValue': [max_val],
            'length': [end - start]
        })

    def test_tc01_chain_success(self):
        """
        Case 1: TC-01 Chain Success (Normal Overlap)
        R3 (Latest) -> R2 (Middle) -> R1 (Oldest)
        Verify that IDs map correctly across the chain.
        """
        print("\nRunning TC-01: Chain Success (Normal Overlap)...")
        
        # R3 (Latest): 104-114, Peak 108
        r3 = self.create_df('R3_01', 104, 114, 108)
        # R2 (Prev1): 102-112, Peak 106
        r2 = self.create_df('R2_01', 102, 112, 106)
        # R1 (Prev2): 100-110, Peak 105
        r1 = self.create_df('R1_01', 100, 110, 105)

        # Iteration 1: Latest (R3) vs Prev1 (R2)
        # Intersection: [104, 112]. Peaks 108 & 106 are inside. Match!
        res1 = self.finder.find_repeated(r3, r2, new_id_label="Previous 1")
        
        self.assertFalse(res1.empty, "Iteration 1 should match")
        self.assertEqual(res1.iloc[0]['Previous 1'], 'R2_01')

        # Iteration 2: Result vs Prev2 (R1)
        # Intersection (R3 vs R1): [104, 110]. Peaks 108 & 105 are inside. Match!
        res2 = self.finder.find_repeated(res1, r1, new_id_label="Previous 2")

        self.assertFalse(res2.empty, "Iteration 2 should match")
        # Check Final Logic: Latest ID, Prev1 ID, Prev2 ID
        row = res2.iloc[0]
        self.assertEqual(row['id'], 'R3_01')
        self.assertEqual(row['Previous 1'], 'R2_01')
        self.assertEqual(row['Previous 2'], 'R1_01')
        print("PASSED: Chain preserved correctly.")

    def test_tc02_broken_chain(self):
        """
        Case 2: TC-02 Broken Chain (Gap)
        R3 overlaps R1, but R2 (Middle) is far away.
        The chain should break at R2, resulting in empty final output.
        """
        print("\nRunning TC-02: Broken Chain (Gap)...")
        
        # R3: 100-110, Peak 105
        r3 = self.create_df('R3_01', 100, 110, 105)
        # R2: 200-210, Peak 205 (Far away)
        r2 = self.create_df('R2_01', 200, 210, 205)
        # R1: 100-110, Peak 105 (Matches R3, but R2 is the link)
        r1 = self.create_df('R1_01', 100, 110, 105)

        # Iteration 1: R3 vs R2
        res1 = self.finder.find_repeated(r3, r2, new_id_label="Previous 1")
        
        self.assertTrue(res1.empty, "Chain should break at R2 because of no overlap")
        
        # Iteration 2: Result (Empty) vs R1
        res2 = self.finder.find_repeated(res1, r1, new_id_label="Previous 2")
        self.assertTrue(res2.empty, "Final result should be empty")
        print("PASSED: Chain correctly broken.")

    def test_tc03_peak_drift(self):
        """
        Case 3: TC-03 Peak Drift (Geometry Overlap but Max Fail)
        Overlap exists, but Max Locations are outside the intersection.
        """
        print("\nRunning TC-03: Peak Drift (Geometry Overlap but Max Fail)...")
        # R1: 100-200, Max 110
        # R2: 150-250, Max 240
        # Intersection: 150-200
        # Max R1 (110) < 150 (Outside)
        # Max R2 (240) > 200 (Outside)
        
        latest = self.create_df('L_01', 150, 250, 240) # R2
        prev = self.create_df('P_01', 100, 200, 110)   # R1

        res = self.finder.find_repeated(latest, prev, new_id_label="Previous 1")
        
        self.assertTrue(res.empty, "Should fail because peaks are outside intersection")
        print("PASSED: Peak drift correctly rejected.")

    def test_tc04_overlap_scenarios(self):
        """
        Case 4: The 4 Overlap Scenarios
        1. Left Overlap (Old starts before, ends inside)
        2. Right Overlap (Old starts inside, ends after)
        3. Inside (Old is inside New)
        4. Encompass (Old covers New)
        Constraint: Peaks must be valid.
        """
        print("\nRunning TC-04: The 4 Overlap Scenarios...")
        
        # Base (Latest): 100-200. Peak 150.
        base = self.create_df('Base', 100, 200, 150)

        # Scenario 1: Left Overlap
        # Old: 50-160. Peak 150. Intersection: [100, 160]. Peak 150 is valid.
        old1 = self.create_df('Old1', 50, 160, 150)
        res1 = self.finder.find_repeated(base, old1, "P1")
        self.assertFalse(res1.empty, "Scenario 1 (Left Overlap) Failed")

        # Scenario 2: Right Overlap
        # Old: 140-250. Peak 150. Intersection: [140, 200]. Peak 150 is valid.
        old2 = self.create_df('Old2', 140, 250, 150)
        res2 = self.finder.find_repeated(base, old2, "P1")
        self.assertFalse(res2.empty, "Scenario 2 (Right Overlap) Failed")

        # Scenario 3: Inside (Old is smaller)
        # Old: 140-160. Peak 150. Intersection: [140, 160]. Peak 150 is valid.
        old3 = self.create_df('Old3', 140, 160, 150)
        res3 = self.finder.find_repeated(base, old3, "P1")
        self.assertFalse(res3.empty, "Scenario 3 (Inside) Failed")

        # Scenario 4: Encompass (Old is larger)
        # Old: 50-250. Peak 150. Intersection: [100, 200]. Peak 150 is valid.
        old4 = self.create_df('Old4', 50, 250, 150)
        res4 = self.finder.find_repeated(base, old4, "P1")
        self.assertFalse(res4.empty, "Scenario 4 (Encompass) Failed")
        
        print("PASSED: All 4 Overlap Scenarios verified.")

if __name__ == '__main__':
    unittest.main()
