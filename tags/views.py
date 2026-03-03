from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Max, Min, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import TagForm
from .models import Tag, TransactionTag


class TagListView(ListView):
    model = Tag
    template_name = "tags/tag_list.html"
    context_object_name = "tags"

    def get_queryset(self):
        return Tag.objects.filter(is_active=True).annotate(
            transaction_count=Count("transaction_tags"),
            loan_count=Count("loan_tags"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context["tags"]
        context["places"] = qs.filter(tag_type=Tag.PLACE)
        context["groups"] = qs.filter(tag_type=Tag.GROUP)
        return context


class TagCreateView(CreateView):
    model = Tag
    form_class = TagForm
    template_name = "tags/tag_form.html"
    success_url = reverse_lazy("tags:list")

    def form_valid(self, form):
        messages.success(self.request, "Tag created successfully.")
        return super().form_valid(form)


class TagUpdateView(UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "tags/tag_form.html"
    success_url = reverse_lazy("tags:list")

    def form_valid(self, form):
        messages.success(self.request, "Tag updated successfully.")
        return super().form_valid(form)


class TagDetailView(DetailView):
    model = Tag
    template_name = "tags/tag_detail.html"
    context_object_name = "tag"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.object
        txn_tags = (
            TransactionTag.objects.filter(tag=tag)
            .select_related("transaction__category", "transaction__account")
            .order_by("-transaction__date")
        )
        context["transaction_tags"] = txn_tags
        context["total"] = txn_tags.aggregate(
            total=Sum("transaction__amount")
        )["total"] or Decimal("0.00")
        return context


class TagGroupsView(ListView):
    model = Tag
    template_name = "tags/tag_groups.html"
    context_object_name = "groups"

    def get_queryset(self):
        return (
            Tag.objects.filter(tag_type=Tag.GROUP, is_active=True)
            .annotate(
                transaction_count=Count("transaction_tags"),
                total_amount=Sum("transaction_tags__transaction__amount"),
                date_min=Min("transaction_tags__transaction__date"),
                date_max=Max("transaction_tags__transaction__date"),
            )
            .order_by("-total_amount")
        )


class TagPlacesView(ListView):
    model = Tag
    template_name = "tags/tag_places.html"
    context_object_name = "places"

    def get_queryset(self):
        return (
            Tag.objects.filter(tag_type=Tag.PLACE, is_active=True)
            .annotate(
                transaction_count=Count("transaction_tags"),
                total_spent=Sum(
                    "transaction_tags__transaction__amount",
                    filter=Q(transaction_tags__transaction__type="expense"),
                ),
            )
            .order_by("-total_spent")
        )


class TagArchiveView(View):
    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        tag.is_active = False
        tag.save()
        messages.success(request, f'Tag "{tag.name}" archived.')
        return redirect("tags:list")


def tag_search(request):
    """HTMX endpoint: search active tags by name."""
    q = request.GET.get("q", "").strip()
    tag_type = request.GET.get("tag_type", "")
    tags = Tag.objects.filter(is_active=True)
    if tag_type:
        tags = tags.filter(tag_type=tag_type)
    if q:
        tags = tags.filter(name__icontains=q)
    else:
        tags = tags.none()
    html = render_to_string(
        "tags/partials/_tag_search_results.html",
        {"tags": tags[:10], "q": q, "tag_type": tag_type},
    )
    return HttpResponse(html)


def tag_create_inline(request):
    """HTMX endpoint: create a new tag inline and return a chip."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        tag_type = request.POST.get("tag_type", "")
        if name and tag_type in ("place", "group"):
            tag, created = Tag.objects.get_or_create(
                name=name,
                tag_type=tag_type,
                defaults={"is_active": True},
            )
            html = render_to_string(
                "tags/partials/_tag_chip.html",
                {"tag": tag},
            )
            return HttpResponse(html)
    return HttpResponse("")
