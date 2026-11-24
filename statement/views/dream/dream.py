from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST

from statement.forms.dream.document import DreamDocumentForm
from statement.forms.dream.dream import DreamForm
from statement.forms.dream.photo import DreamPhotoForm
from statement.models import Dream, DreamDocument, DreamPhoto
from statement.services.dream.dream import DreamService
from statement.views.base_view import BaseView


class DreamView(BaseView):
    """
    View responsável pela gestão das categorias
    """

    class_has_user = True
    class_title = 'Sonhos'
    class_form = DreamForm
    model = Dream
    service = DreamService
    redirect_url = reverse_lazy('get_dreams_by_status', args=['ativos'])

    def __init__(self):
        """
        Atualiza o dicionário template_is_global sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.template_is_global.update(
            {
                'detail': False,
                'get_all': False,
                'update': False,
            }
        )

    @method_decorator(login_required)
    def get_by_status(self, request, status):
        """
        Obtem sonhos de acordo com o status.

        Status não é um atributo do model, ele é definido pela data atual.
        """
        if status == 'ativos':
            dreams = self.service.get_active_dreams(request.user)
        elif status == 'realizados':
            dreams = self.service.get_completed_dreams(request.user)
        elif status == 'pausados':
            dreams = self.service.get_paused_dreams(request.user)
        elif status == 'cancelados':
            dreams = self.service.get_cancelled_dreams(request.user)
        else:
            raise Http404('Status inválido')
        specific_content = {
            'instances': dreams,
            'dream_status': status,
            'completed_dream_groups': self._group_completed_dreams_by_year(dreams) if status == 'realizados' else [],
        }
        return self._render(request, None, 'dream/list.html', specific_content)

    def _group_completed_dreams_by_year(self, dreams):
        """
        Agrupa sonhos realizados pelo ano da data de conclusão.
        """
        groups_by_year = {}
        for dream in dreams:
            year = dream.completion_date.year if dream.completion_date else None
            groups_by_year.setdefault(year, []).append(dream)

        sorted_years = sorted((year for year in groups_by_year if year), reverse=True)
        grouped_dreams = [
            {
                'title': year,
                'instances': groups_by_year[year],
                'total_spent': sum(dream.total_spent for dream in groups_by_year[year]),
            }
            for year in sorted_years
        ]

        if None in groups_by_year:
            grouped_dreams.append(
                {
                    'title': 'Sem data de conclusão',
                    'instances': groups_by_year[None],
                    'total_spent': sum(dream.total_spent for dream in groups_by_year[None]),
                }
            )

        return grouped_dreams

    def _add_context_on_templatetags(self, request, instance):
        """
        Retorna as transações relacionadas ao sonho.
        A partir de agora, apenas Transactions são usadas (não mais Portion).
        """
        return {
            'transactions': instance.transactions.filter(user=request.user).order_by('-posted_date'),
            'photos': instance.photos.all(),
            'photo_form': DreamPhotoForm(),
            'documents': instance.documents.all(),
            'document_form': DreamDocumentForm(),
        }

    @method_decorator(login_required)
    @method_decorator(require_POST)
    def upload_photos(self, request, id):
        dream = self._get_instance(request, id)
        form = DreamPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            saved = []
            try:
                with transaction.atomic():
                    Dream.objects.select_for_update().get(pk=dream.pk)
                    last_position = dream.photos.aggregate(last=Max('position'))['last']
                    next_position = last_position + 1 if last_position is not None else 0
                    for offset, image in enumerate(form.cleaned_data['photos']):
                        photo = DreamPhoto(dream=dream, image=image, position=next_position + offset)
                        saved.append(photo)
                        photo.save()
            except Exception:
                for photo in saved:
                    if photo.image and photo.image._committed:
                        photo.image.delete(save=False)
                raise
            messages.success(request, 'Fotos adicionadas ao sonho.')
            return redirect('detail_dream', id=dream.pk)
        self._context = 'detail'
        context = self._add_context_on_templatetags(request, dream)
        context.update(instance=dream, photo_form=form)
        return self._render(request, None, 'dream/detail.html', context)

    @method_decorator(login_required)
    @method_decorator(require_POST)
    def delete_photo(self, request, id, photo_id):
        dream = self._get_instance(request, id)
        with transaction.atomic():
            Dream.objects.select_for_update().get(pk=dream.pk)
            get_object_or_404(DreamPhoto, dream=dream, pk=photo_id).delete()
        messages.success(request, 'Foto removida.')
        return redirect('detail_dream', id=dream.pk)

    @method_decorator(login_required)
    @method_decorator(require_POST)
    def reorder_photos(self, request, id):
        dream = self._get_instance(request, id)
        try:
            photo_ids = [int(value) for value in request.POST.getlist('photo_ids')]
        except ValueError:
            return JsonResponse({'error': 'Ordem inválida.'}, status=400)
        with transaction.atomic():
            Dream.objects.select_for_update().get(pk=dream.pk)
            photos = {photo.pk: photo for photo in dream.photos.all()}
            if len(photo_ids) != len(photos) or set(photo_ids) != set(photos):
                return JsonResponse({'error': 'A galeria mudou. Atualize a página e tente novamente.'}, status=400)
            for position, photo_id in enumerate(photo_ids):
                photos[photo_id].position = position
            DreamPhoto.objects.bulk_update(photos.values(), ['position'])
        return JsonResponse({'saved': True})

    @method_decorator(login_required)
    @method_decorator(require_GET)
    def photo(self, request, id, photo_id):
        dream = self._get_instance(request, id)
        photo = get_object_or_404(DreamPhoto, dream=dream, pk=photo_id)
        try:
            response = FileResponse(photo.image.open('rb'))
        except FileNotFoundError as error:
            raise Http404 from error
        response['Cache-Control'] = 'private, no-store'
        return response

    @method_decorator(login_required)
    @method_decorator(require_POST)
    def upload_documents(self, request, id):
        dream = self._get_instance(request, id)
        form = DreamDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            saved = []
            try:
                with transaction.atomic():
                    for file in form.cleaned_data['documents']:
                        document = DreamDocument(dream=dream, file=file, name=file.name, size=file.size)
                        saved.append(document)
                        document.save()
            except Exception:
                for document in saved:
                    if document.file and document.file._committed:
                        document.file.delete(save=False)
                raise
            messages.success(request, 'Documentos adicionados ao sonho.')
            return redirect('detail_dream', id=dream.pk)
        self._context = 'detail'
        context = self._add_context_on_templatetags(request, dream)
        context.update(instance=dream, document_form=form)
        return self._render(request, None, 'dream/detail.html', context)

    @method_decorator(login_required)
    @method_decorator(require_POST)
    def delete_document(self, request, id, document_id):
        dream = self._get_instance(request, id)
        get_object_or_404(DreamDocument, dream=dream, pk=document_id).delete()
        messages.success(request, 'Documento removido.')
        return redirect('detail_dream', id=dream.pk)

    @method_decorator(login_required)
    @method_decorator(require_GET)
    def document(self, request, id, document_id):
        dream = self._get_instance(request, id)
        document = get_object_or_404(DreamDocument, dream=dream, pk=document_id)
        try:
            response = FileResponse(
                document.file.open('rb'),
                content_type='application/pdf',
                filename=document.name,
                as_attachment=request.GET.get('download') == '1',
            )
        except FileNotFoundError as error:
            raise Http404 from error
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
