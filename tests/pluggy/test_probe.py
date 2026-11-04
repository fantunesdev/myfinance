"""Offline tests: never require credentials, Django, or financial data."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

SPEC = importlib.util.spec_from_file_location("pluggy_probe", Path(__file__).parents[2] / "scripts/pluggy_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def response(payload, status=200):
    result = Mock(status_code=status, headers={})
    result.json.return_value = payload
    return result


class ReaderTests(unittest.TestCase):
    def reader(self, responses):
        session = Mock()
        session.request.side_effect = responses
        return probe.PluggyReader("client", "secret", session=session, sleep=Mock())

    def test_cursor_consumes_every_page_and_keeps_encoded_cursor(self):
        cursor = "?accountId=account&after=abc%2B%2F%3D"
        reader = self.reader(
            [
                response({"results": [{"id": "t1", "accountId": "account"}], "next": cursor}),
                response({"results": [{"id": "t2", "accountId": "account"}], "next": None}),
            ]
        )
        self.assertEqual(len(reader.transactions("account")), 2)
        self.assertEqual(reader.session.request.call_args.kwargs["params"], cursor[1:])
        for call in reader.session.request.call_args_list:
            self.assertEqual(call.args[0], "GET")
            self.assertFalse(call.kwargs["allow_redirects"])

    def test_bills_pagination_checks_total(self):
        reader = self.reader(
            [
                response({"page": 1, "total": 2, "totalPages": 2, "results": [{"id": "b1"}]}),
                response({"page": 2, "total": 2, "totalPages": 2, "results": [{"id": "b2"}]}),
            ]
        )
        self.assertEqual(len(reader.numbered("/bills", {"accountId": "a"})), 2)

    def test_incomplete_numbered_pagination_fails(self):
        reader = self.reader([response({"page": 1, "total": 2, "totalPages": 1, "results": [{"id": "b1"}]})])
        with self.assertRaises(probe.ProbeError):
            reader.numbered("/bills", {})

    def test_missing_cursor_termination_and_other_account_fail(self):
        for payload in ({"results": []}, {"results": [{"id": "x", "accountId": "other"}], "next": None}):
            with self.subTest(payload=payload), self.assertRaises(probe.ProbeError):
                self.reader([response(payload)]).transactions("account")

    def test_repeated_cursor_or_duplicate_id_fails(self):
        for second in (
            {"results": [{"id": "t2", "accountId": "a"}], "next": "?after=x"},
            {"results": [{"id": "t1", "accountId": "a"}], "next": None},
        ):
            reader = self.reader(
                [
                    response({"results": [{"id": "t1", "accountId": "a"}], "next": "?after=x"}),
                    response(second),
                ]
            )
            with self.assertRaises(probe.ProbeError):
                reader.transactions("a")

    def test_does_not_allow_financial_writes(self):
        reader = self.reader([])
        with self.assertRaises(probe.ProbeError):
            reader.request("/payments/intents")
        reader.session.request.assert_not_called()

    def test_reauth_once_without_exposing_secret(self):
        reader = self.reader([response({}, 401), response({"apiKey": "new"}), response({"id": "ok"})])
        self.assertEqual(reader.request("/accounts"), {"id": "ok"})
        self.assertEqual([c.args[0] for c in reader.session.request.call_args_list], ["GET", "POST", "GET"])
        self.assertEqual(reader.session.request.call_args.kwargs["headers"], {"X-API-KEY": "new"})

    def test_errors_are_sanitized_and_retries_bounded(self):
        reader = self.reader([requests.ConnectionError("secret response")] * 3)
        with self.assertRaises(probe.ProbeError) as caught:
            reader.request("/accounts")
        self.assertNotIn("secret", str(caught.exception))
        self.assertEqual(reader.session.request.call_count, 3)
        reader = self.reader([response({"secret": "private"}, 429)] * 3)
        with self.assertRaises(probe.ProbeError):
            reader.request("/accounts")
        self.assertEqual(reader.session.request.call_count, 3)

    def test_bill_diagnostics_separate_credit_from_debit(self):
        summary = probe.summarize(
            {"id": "a", "balance": 150},
            [{"id": "b", "totalAmount": 100}],
            [
                {
                    "id": "t1",
                    "type": "DEBIT",
                    "amount": 100,
                    "creditCardMetadata": {"billId": "b", "cardNumber": "1234"},
                },
                {"id": "t2", "type": "CREDIT", "amount": -80, "creditCardMetadata": {"billId": "b"}},
            ],
        )
        self.assertEqual(summary["usedLimit"], 150)
        self.assertEqual(summary["bills"][0]["signedAmountByType"], {"DEBIT": "100", "CREDIT": "-80"})
        self.assertEqual(summary["cardNumbers"]["não identificado"], 1)

    def test_full_export_and_private_permissions_without_django(self):
        reader = self.reader(
            [
                response({"apiKey": "private-key"}),
                response({"status": "UPDATED"}),
                response(
                    {
                        "page": 1,
                        "total": 2,
                        "totalPages": 1,
                        "results": [
                            {"id": "bank", "type": "BANK", "subtype": "CHECKING_ACCOUNT"},
                            {"id": "card", "type": "CREDIT", "subtype": "CREDIT_CARD", "owner": "private-name"},
                        ],
                    }
                ),
                response({"page": 1, "total": 0, "totalPages": 0, "results": []}),
                response({"results": [], "next": None}),
            ]
        )
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / "export"
            with patch.dict(
                os.environ,
                {
                    "PLUGGY_CLIENT_ID": "client",
                    "PLUGGY_CLIENT_SECRET": "secret-value",
                    "PLUGGY_ITEM_ID": "00000000-0000-0000-0000-000000000001",
                    "PLUGGY_ACCOUNT_ID": "",
                },
            ), patch.object(probe, "PluggyReader", return_value=reader), patch("builtins.print"):
                self.assertEqual(probe.main(["--output-dir", str(directory)]), 0)
            content = (directory / "snapshot.json").read_text()
            self.assertNotIn("private-key", content)
            self.assertNotIn("secret-value", content)
            self.assertNotIn("private-name", content)
            self.assertEqual(len(json.loads(content)["creditAccounts"]), 1)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual((directory / "snapshot.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(reader.session.request.call_count, 5)

    def test_failed_collection_does_not_publish_snapshot(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / "export"
            with patch.dict(
                os.environ,
                {
                    "PLUGGY_CLIENT_ID": "client",
                    "PLUGGY_CLIENT_SECRET": "secret",
                    "PLUGGY_ITEM_ID": "00000000-0000-0000-0000-000000000001",
                    "PLUGGY_ACCOUNT_ID": "",
                },
            ), patch.object(probe, "collect", side_effect=probe.ProbeError("consulta incompleta")), patch(
                "builtins.print"
            ):
                self.assertEqual(probe.main(["--output-dir", str(directory)]), 1)
            self.assertFalse(directory.exists())


if __name__ == "__main__":
    unittest.main()
