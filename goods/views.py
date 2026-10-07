from typing import Any

from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from goods.models import Category, Items

ITEMS_PER_PAGE = 30


def index_view(request: WSGIRequest) -> HttpResponse:
    context: dict[str, Any] = {}

    # Categories -> context (whole tree with a single query)
    categories = list(Category.objects.only("id", "name", "parent_id").order_by("id"))
    if not categories:
        raise Http404("No categories found")
    tree = []
    nodes: dict[int, dict[str, Any]] = {
        cat.pk: {"id": cat.pk, "name": cat.name, "children": []} for cat in categories
    }
    for cat in categories:
        node = nodes[cat.pk]
        if cat.parent_id:
            nodes[cat.parent_id]["children"].append(node)
        else:
            tree.append(node)
    context["categories"] = tree

    # Items by categories -> context
    category_id = request.GET.get("category")
    products = Items.objects.only("id", "name", "price", "description", "sku").order_by("id")
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        context["selected_category"] = selected_category
        products = products.filter(category=selected_category)
    context["products"] = Paginator(products, ITEMS_PER_PAGE).get_page(request.GET.get("page"))

    return render(request, "index.html", context)
