import uuid

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from investments.forms.base import DateInput
from investments.models import InvestmentProduct, ProductValuation
from investments.services.investment import InvestmentService
from investments.services.products import display_positions, record_valuation


class ProductValuationForm(forms.Form):
    date = forms.DateField(label='Data do saldo', widget=DateInput())
    value = forms.DecimalField(label='Saldo do produto em reais', max_digits=14, decimal_places=2, min_value=0)
    basis = forms.ChoiceField(label='Tipo do saldo', choices=ProductValuation._meta.get_field('basis').choices)
    source = forms.CharField(label='Origem do saldo', max_length=120)
    evidence = forms.CharField(label='Comprovante ou observação da conferência', widget=forms.Textarea())
    reference_key = forms.CharField(max_length=100, widget=forms.HiddenInput())


@login_required
def product_detail(request, pk):
    product = get_object_or_404(
        InvestmentProduct.objects.select_related('broker').prefetch_related('valuations'), pk=pk, user=request.user
    )
    lots = (
        product.lots.filter(user=request.user)
        .select_related('asset', 'broker', 'product')
        .prefetch_related('transactions')
    )
    positions = [InvestmentService.get_position(lot) for lot in lots]
    displayed = display_positions(request.user, positions)
    position = next((p for p in displayed if p.get('product') and p['product'].pk == product.pk), None)
    form = ProductValuationForm(
        request.POST or None,
        initial={
            'date': timezone.localdate(),
            'basis': 'gross',
            'source': str(product.broker),
            'reference_key': uuid.uuid4().hex,
        },
    )
    if request.method == 'POST' and form.is_valid():
        try:
            record_valuation(request.user, product, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Avaliação registrada. Os comprovantes e movimentos dos lotes foram preservados.')
            return redirect('detail_investment_product', pk=product.pk)
    return render(
        request,
        'investments/product_detail.html',
        {
            'product': product,
            'position': position,
            'lots': positions,
            'valuations': product.valuations.order_by('-date', '-id'),
            'form': form,
        },
    )
