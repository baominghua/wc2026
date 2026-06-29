import unittest
from pathlib import Path


REVIEW_PAGE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "ReviewPage.tsx"


class ReviewPageContractTests(unittest.TestCase):
    def test_review_page_uses_only_independent_score_metrics(self):
        source = REVIEW_PAGE.read_text(encoding="utf-8")

        self.assertIn("胜平负命中", source)
        self.assertIn("wdl_accuracy", source)
        self.assertIn("wdl_hit", source)
        self.assertIn("1选命中", source)
        self.assertIn("2选命中", source)
        self.assertIn("3选命中", source)
        self.assertIn("冷门命中", source)
        self.assertIn("总命中率", source)
        self.assertIn("score_total_accuracy", source)
        self.assertIn("totalTournamentMatches", source)
        self.assertIn("audit.summary.total_matches", source)
        self.assertNotIn("`${audit.summary.reviewed_matches}/${audit.summary.completed_matches}`", source)
        self.assertNotIn("outcome_top1_accuracy", source)
        self.assertNotIn("赛果 1选", source)
        self.assertNotIn("候选池总命中", source)


if __name__ == "__main__":
    unittest.main()
