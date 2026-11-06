"""Downloads of original bank data, scoped by ledger_data to the owner and bill."""
import csv
from collections import defaultdict
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .services import money


EVENTS = {
    "purchase": "Compra/taxa",
    "card_payment": "Pagamento da fatura",
    "refund": "Estorno/crédito",
    "unknown": "Revisar",
}


def selected_cards(data, identifiers):
    available = {f'{group["account_id"]}:{group["last_four"]}' for group in data["groups"]}
    requested = set(identifiers)
    if not requested or not requested <= available:
        raise ValidationError("Selecione ao menos um cartão disponível nesta fatura para exportar o PDF.")
    groups = [group for group in data["groups"] if f'{group["account_id"]}:{group["last_four"]}' in requested]
    totals = defaultdict(lambda: {field: money(0) for field in ("charges", "refunds", "payments", "net")})
    for group in groups:
        for field in ("charges", "refunds", "payments", "net"):
            totals[group["currency"]][field] += group[field]
    return {
        **data,
        "groups": groups,
        "totals": dict(totals),
        "count": sum(len(group["rows"]) for group in groups),
        "partial_selection": len(groups) != len(data["groups"]),
    }


def date_label(value):
    return "/".join(str(value)[:10].split("-")[::-1]) if value else "Sem fatura definida"


def amount_label(value):
    return f"{money(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def spreadsheet_text(value):
    text = str(value or "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


def export_filename(data, extension):
    bill = next((bill for bill in data["bills"] if bill["id"] == data["selected_bill"]), None)
    banks = list(dict.fromkeys(data.get("bank_names", [])))
    bank = "-".join(slugify(name).title() for name in banks if name) or "Banco"
    if bill and bill["due_date"]:
        name = f'Fatura-{bank}-{str(bill["due_date"])[:7]}'
    else:
        name = f"Faturas-{bank}-todas" if data["selected_bill"] == "all" else f"Fatura-{bank}-sem-fatura-definida"
    return f'attachment; filename="{name}.{extension}"'


def csv_response(data):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = export_filename(data, "csv")
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Data da compra",
            "Data do lançamento",
            "Vencimento da fatura",
            "Conta/cartão",
            "Final do cartão",
            "Descrição original",
            "Parcela",
            "Valor",
            "Moeda",
            "Evento",
            "Situação da importação",
            "Nome do cartão",
        ]
    )
    for group in data["groups"]:
        for row in group["rows"]:
            facts = row["facts"]
            parcel = f'{facts["number"]}/{facts["total"]}' if facts["payment_type"] == "INSTALLMENT" else "À vista"
            writer.writerow(
                [
                    date_label(facts.get("purchase_date") or facts["date"]),
                    date_label(facts["date"]),
                    date_label(row["due_date"]),
                    spreadsheet_text(group["account"]),
                    group["last_four"],
                    spreadsheet_text(facts["description"]),
                    parcel,
                    str(money(facts["amount"])).replace(".", ","),
                    spreadsheet_text(facts["currency"]),
                    EVENTS[row["event"]],
                    row["state"],
                    spreadsheet_text(group.get("card_name")),
                ]
            )
    return response


def pdf_brands(user, data):
    from .models import ExternalAccount

    account_ids = {group["account_id"] for group in data["groups"]}
    if not account_ids:
        account_ids.update(bill["account_id"] for bill in data["bills"] if bill["id"] == data["selected_bill"])
    brands = []
    for account in ExternalAccount.objects.filter(pk__in=account_ids, connection__user=user).select_related(
        "card__account__bank"
    ):
        card = account.card if account.card_id and account.card.user_id == user.pk else None
        bank = card.account.bank if card and card.account_id else None
        brands.append(
            {
                "name": card.description if card else account.name,
                "bank_name": bank.description if bank else card.description if card else account.name,
                "images": [image for image in (card.icon if card else None, bank.icon if bank else None) if image],
            }
        )
    return brands


def pdf_response(data, brands=()):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    stream = BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=" · ".join(brand["name"] for brand in brands) or "Faturas",
    )
    story = []
    for brand in brands:
        logo = None
        for image in brand["images"]:
            try:
                with image.open("rb") as source:
                    candidate = Image(BytesIO(source.read()))
                ratio = min(48 * mm / candidate.imageWidth, 20 * mm / candidate.imageHeight)
                candidate.drawWidth = candidate.imageWidth * ratio
                candidate.drawHeight = candidate.imageHeight * ratio
                candidate.hAlign = "LEFT"
                logo = candidate
                break
            except (OSError, ValueError):
                continue
        story.append(logo or Paragraph(escape(brand["name"]), styles["Title"]))
        story.append(Spacer(1, 5 * mm))
    bill = next((bill for bill in data["bills"] if bill["id"] == data["selected_bill"]), None)
    if bill:
        total = bill["total"]
        summary = (
            f'Vencimento: {date_label(bill["due_date"])}<br/>'
            f'Total: {amount_label(total)} {escape(bill["currency"])}'
        )
        story.append(
            Paragraph(
                summary,
                styles["Normal"],
            )
        )
    else:
        story.append(
            Paragraph("Todas as faturas" if data["selected_bill"] == "all" else "Sem fatura definida", styles["Normal"])
        )
    story.append(Spacer(1, 5 * mm))
    if not data["count"]:
        story.append(Paragraph("Nenhum lançamento nesta seleção.", styles["Normal"]))
    for group in data["groups"]:
        # The all-bills selection must retain each bill's identity within a card.
        by_bill = defaultdict(list)
        for row in group["rows"]:
            by_bill[(row["facts"]["bill_id"], row["due_date"])].append(row)
        for (_, due), rows in by_bill.items():
            name = f'{escape(group["card_name"])} · ' if group.get("card_name") else ""
            heading = f'{escape(group["account"])} · {name}Final {escape(group["last_four"] or "não informado")} · {date_label(due)}'
            story.append(Paragraph(heading, styles["Heading2"]))
            for payments in (False, True):
                selected = [row for row in rows if (row["event"] == "card_payment") == payments]
                if not selected:
                    continue
                if payments:
                    story.append(Paragraph("Pagamentos da fatura (separados dos gastos)", styles["Heading3"]))
                cells = [["Data da compra", "Descrição original", f'Valor ({group["currency"]})']]
                for row in selected:
                    facts = row["facts"]
                    description = facts["description"]
                    if facts["payment_type"] == "INSTALLMENT":
                        description += f' · Parcela {facts["number"]}/{facts["total"]}'
                    cells.append(
                        [
                            date_label(facts.get("purchase_date") or facts["date"]),
                            Paragraph(escape(description), styles["BodyText"]),
                            amount_label(facts["amount"]),
                        ]
                    )
                table = LongTable(cells, colWidths=[30 * mm, 116 * mm, 32 * mm], repeatRows=1, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 7),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
                        ]
                    )
                )
                story.append(table)
                total = sum(
                    (abs(money(row["facts"]["amount"])) * (-1 if row["event"] == "refund" else 1) for row in selected),
                    money(0),
                )
                story.append(
                    Paragraph(
                        f'{"Pagamentos" if payments else "Total de gastos, descontados os créditos"}: '
                        f'{amount_label(total)} {escape(group["currency"])}',
                        styles["Normal"],
                    )
                )
                story.append(Spacer(1, 4 * mm))
    for currency, total in data["totals"].items():
        story.append(
            Paragraph(f'Total de gastos ({escape(currency)}): {amount_label(total["net"])}', styles["Heading3"])
        )

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Página {doc.page}")

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(stream.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = export_filename(data, "pdf")
    return response
