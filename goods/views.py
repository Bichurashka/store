from typing import Any

from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from goods.models import Category, Items


def index_view(request: WSGIRequest) -> HttpResponse:
    context: dict[str, Any] = {}

    # View some of the latest added items on the homepage
    amount_to_display = 4
    goods = Items.objects.all().order_by("-id")[:amount_to_display]
    context["goods"] = goods

    # Categories -> context
    categories = Category.objects.all()
    if not categories:
        raise Http404("No categories found")
    tree = []
    nodes: dict[str, dict[str, Any]] = {
        cat.name: {"name": cat.name, "children": []} for cat in categories
    }
    for cat in categories:
        node = nodes[cat.name]
        if cat.parent:
            nodes[cat.parent.name]["children"].append(node)
        else:
            tree.append(node)
    context["categories"] = tree

    # Items by categories -> context
    category_id = request.GET.get("category")
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        products = Items.objects.filter(category=selected_category)
    else:
        products = Items.objects.all()
    context["products"] = products

    return render(request, "index.html", context)
