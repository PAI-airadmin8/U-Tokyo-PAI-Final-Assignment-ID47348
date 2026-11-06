import unittest
from integrated_entrypoint import check_reply


class GateChecks(unittest.TestCase):
    def setUp(self):
        self.reply = {"session_id": "x" * 32, "seq": 1, "label": "paper",
                      "confidence": .9, "policy_sha256": "abc", "safety": "PICK"}
        self.params = dict(session="x" * 32, seq=1, policy_sha="abc")

    def test_pick(self):
        self.assertEqual(check_reply(self.reply, **self.params), "PICK")

    def test_personal_skip(self):
        self.reply.update(label="personal", safety="SKIP")
        self.assertEqual(check_reply(self.reply, **self.params), "SKIP")

    def test_low_confidence_skip(self):
        self.reply.update(confidence=.7, safety="SKIP")
        self.assertEqual(check_reply(self.reply, **self.params), "SKIP")

    def test_stale_or_replayed_reply(self):
        self.reply["session_id"] = "bad"
        with self.assertRaises(ValueError):
            check_reply(self.reply, **self.params)

    def test_wrong_policy_hash(self):
        self.reply["policy_sha256"] = "another"
        with self.assertRaises(ValueError):
            check_reply(self.reply, **self.params)

    def test_personal_cannot_be_pick(self):
        self.reply.update(label="personal", safety="PICK")
        with self.assertRaises(ValueError):
            check_reply(self.reply, **self.params)

    def test_nan_confidence(self):
        self.reply["confidence"] = float("nan")
        with self.assertRaises(ValueError):
            check_reply(self.reply, **self.params)


if __name__ == "__main__":
    unittest.main()
