from typing import Any, Callable

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response


def is_admin(*methods: str) -> Callable[[Callable[..., Response]], Callable[..., Response]]:
    def decorator(func: Callable[..., Response]) -> Callable[..., Response]:
        def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
            if request.method in methods:
                if request.user.is_staff:
                    return func(request, *args, **kwargs)
                return Response(
                    {"detail": "Only admins can create categories"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
