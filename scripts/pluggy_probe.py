"""Read-only personal Pluggy probe. No Django or database initialization."""

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Support direct execution from the scripts directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clients.pluggy.reader import PluggyReader, ProbeError


def summarize(account, bills, transactions):
    cards = Counter(
        (row.get("creditCardMetadata") or {}).get("cardNumber") or "não identificado" for row in transactions
    )
    bill_rows = []
    for bill in bills:
        linked = [row for row in transactions if (row.get("creditCardMetadata") or {}).get("billId") == bill["id"]]
        sums = {
            kind: str(sum((Decimal(str(row["amount"])) for row in linked if row.get("type") == kind), Decimal(0)))
            for kind in ("DEBIT", "CREDIT")
        }
        bill_rows.append(
            {
                "id": bill["id"],
                "dueDate": bill.get("dueDate"),
                "billClosingDate": bill.get("billClosingDate"),
                "totalAmount": bill.get("totalAmount"),
                "currencyCode": bill.get("totalAmountCurrencyCode"),
                "transactionCount": len(linked),
                "signedAmountByType": sums,
            }
        )
    return {
        "accountId": account["id"],
        "usedLimit": account.get("balance"),
        "currencyCode": account.get("currencyCode"),
        "transactionCount": len(transactions),
        "statuses": dict(Counter(row.get("status", "missing") for row in transactions)),
        "cardNumbers": dict(cards),
        "bills": bill_rows,
        "note": "Somas por tipo são diagnósticas; não descontar pagamentos anteriores nem ignorar estornos automaticamente.",
    }


def collect(reader, item_id, account_id=None):
    reader.authenticate()
    item = reader.request("/items/" + item_id)
    accounts = reader.numbered("/accounts", {"itemId": item_id, "type": "CREDIT"})
    accounts = [a for a in accounts if a.get("type") == "CREDIT" and a.get("subtype") == "CREDIT_CARD"]
    if account_id:
        accounts = [a for a in accounts if a["id"] == account_id]
    if not accounts:
        raise ProbeError(
            "Nenhum cartão disponível para a conexão/filtro informado; confira consentimento e sincronização."
        )
    results = []
    for account in accounts:
        bills = reader.numbered("/bills", {"accountId": account["id"]})
        transactions = reader.transactions(account["id"])
        # Avoid exporting account owner, tax number, or unrelated bank accounts.
        safe_account = {
            k: account.get(k) for k in ("id", "type", "subtype", "name", "balance", "currencyCode", "creditData")
        }
        safe_account["creditData"] = {
            k: (account.get("creditData") or {}).get(k)
            for k in (
                "balanceDueDate",
                "balanceCloseDate",
                "creditLimit",
                "availableCreditLimit",
                "minimumPayment",
            )
        }
        results.append(
            {
                "account": safe_account,
                "bills": bills,
                "transactions": transactions,
                "summary": summarize(account, bills, transactions),
            }
        )
    return {
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "paginationComplete": True,
        "scope": "Dados disponíveis na Pluggy; não comprova completude no banco nem força atualização.",
        "item": {k: item.get(k) for k in ("id", "status", "executionStatus", "lastUpdatedAt", "consentExpiresAt")},
        "pagesFetched": dict(reader.pages),
        "creditAccounts": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Consulta pessoal Pluggy, somente leitura, sem banco de dados local.")
    parser.add_argument("--env-file", type=Path, help="Arquivo dotenv explícito; não é carregado automaticamente.")
    parser.add_argument("--output-dir", type=Path, help="Novo diretório privado; padrão: temporário em /tmp.")
    args = parser.parse_args(argv)
    try:
        if args.env_file:
            from dotenv import load_dotenv

            if not args.env_file.is_file():
                raise ProbeError("Arquivo de ambiente não encontrado.")
            load_dotenv(args.env_file, override=False)
        names = ("PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET", "PLUGGY_ITEM_ID")
        missing = [name for name in names if not os.environ.get(name, "").strip()]
        if missing:
            raise ProbeError("Defina: " + ", ".join(missing))
        item_id = os.environ["PLUGGY_ITEM_ID"].strip()
        account_id = os.environ.get("PLUGGY_ACCOUNT_ID", "").strip() or None
        if not PluggyReader._is_uuid(item_id) or (account_id and not PluggyReader._is_uuid(account_id)):
            raise ProbeError("PLUGGY_ITEM_ID/PLUGGY_ACCOUNT_ID deve ser UUID.")
        if args.output_dir and args.output_dir.exists():
            raise ProbeError("Escolha um diretório de saída novo; arquivos anteriores não serão sobrescritos.")
        reader = PluggyReader(os.environ["PLUGGY_CLIENT_ID"], os.environ["PLUGGY_CLIENT_SECRET"])
        snapshot = collect(reader, item_id, account_id)
        directory = args.output_dir or Path(tempfile.mkdtemp(prefix="myfinance-pluggy-", dir="/tmp"))
        if args.output_dir:
            directory.mkdir(mode=0o700, parents=False)
        output = directory / "snapshot.json"
        staging = directory / ".snapshot.tmp"
        with open(staging, "x", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            json.dump(snapshot, stream, indent=2, ensure_ascii=False)
        staging.replace(output)
        print(
            f'Consulta concluída: {len(snapshot["creditAccounts"])} cartão(ões); '
            f'{sum(len(a["transactions"]) for a in snapshot["creditAccounts"])} transações.'
        )
        print(f"Dados privados e resumo por fatura: {output}")
        print("Nenhum lançamento foi gravado no MyFinance. Nenhuma movimentação financeira foi solicitada.")
        return 0
    except (ProbeError, OSError) as error:
        print(
            str(error) if isinstance(error, ProbeError) else "Não foi possível ler/gravar o arquivo local.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
