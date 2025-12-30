import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import CoverageAssignment, Driver, Journalist


def _has_editorial_access(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False):
        return True
    for attr in ("is_editorial_manager", "is_admin"):
        fn = getattr(user, attr, None)
        if callable(fn) and fn():
            return True
    return False


def _api_forbidden():
    return JsonResponse({"ok": False, "error": "forbidden"}, status=403)


def _parse_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads((request.body or b"{}").decode("utf-8"))
        except Exception:
            return {}
    return request.POST


def _photo_url(obj):
    f = getattr(obj, "photo", None)
    if not f:
        return ""
    try:
        url = f.url
    except Exception:
        return ""
    if not url:
        return ""
    return f"{url}?t={int(timezone.now().timestamp())}"


def _journalist_to_card(j: Journalist):
    return {
        "id": str(j.id),
        "name": j.name,
        "email": j.email or "",
        "phone": j.phone or "",
        "status": j.status,
        "status_label": j.get_status_display(),
        "specialties": j.specialties or "",
        "workload_score": j.workload_score or 0,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "photo_url": _photo_url(j),
    }


def _driver_to_card(d: Driver):
    return {
        "id": str(d.id),
        "name": d.name,
        "phone": d.phone or "",
        "status": d.status,
        "status_label": d.get_status_display(),
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "photo_url": _photo_url(d),
    }


def _assignment_payload(a: CoverageAssignment):
    cv = a.coverage
    return {
        "id": str(a.id),
        "status": a.status,
        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "coverage": {
            "id": str(cv.id),
            "title": cv.event_title,
            "date": cv.event_date.isoformat() if cv.event_date else None,
            "time": cv.start_time.strftime("%H:%M") if cv.start_time else None,
            "address": cv.address,
            "status": cv.status,
        },
    }


@login_required
def journalists_page(request):
    if not _has_editorial_access(request.user):
        return render(request, "spot/dashboard.html", status=403)
    return render(request, "editorial/journalists.html")


@login_required
def drivers_page(request):
    if not _has_editorial_access(request.user):
        return render(request, "spot/dashboard.html", status=403)
    return render(request, "editorial/drivers.html")


@login_required
@require_http_methods(["GET", "POST"])
def api_journalists(request):
    if not _has_editorial_access(request.user):
        return _api_forbidden()

    if request.method == "GET":
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        sort = (request.GET.get("sort") or "").strip() or "name_asc"
        try:
            page = int(request.GET.get("page") or "1")
        except Exception:
            page = 1
        try:
            page_size = max(1, min(50, int(request.GET.get("page_size") or "24")))
        except Exception:
            page_size = 24

        qs = Journalist.objects.all()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(specialties__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)

        if sort == "name_desc":
            qs = qs.order_by("-name")
        elif sort == "workload_desc":
            qs = qs.order_by("-workload_score", "name")
        elif sort == "created_desc":
            qs = qs.order_by("-created_at")
        elif sort == "status":
            qs = qs.order_by("status", "name")
        else:
            qs = qs.order_by("name")

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = [_journalist_to_card(j) for j in qs[start:end]]
        num_pages = (total // page_size) + (1 if total % page_size else 0)
        return JsonResponse(
            {
                "ok": True,
                "items": items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "has_prev": page > 1,
                    "has_next": end < total,
                    "num_pages": num_pages,
                },
            }
        )

    payload = _parse_body(request)
    name = (payload.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "name_required"}, status=400)

    j = Journalist.objects.create(
        name=name,
        email=(payload.get("email") or "").strip() or None,
        phone=(payload.get("phone") or "").strip() or None,
        status=(payload.get("status") or "").strip() or "available",
        specialties=(payload.get("specialties") or "").strip(),
    )
    if "photo" in request.FILES:
        j.photo = request.FILES["photo"]
        j.save(update_fields=["photo", "updated_at"])

    return JsonResponse({"ok": True, "item": _journalist_to_card(j)}, status=201)


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def api_journalist_detail(request, journalist_id):
    if not _has_editorial_access(request.user):
        return _api_forbidden()

    j = Journalist.objects.filter(id=journalist_id).first()
    if not j:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    if request.method == "GET":
        assignments = (
            CoverageAssignment.objects.select_related("coverage")
            .filter(journalist=j)
            .order_by("-assigned_at")
        )
        today = timezone.localdate()
        upcoming = []
        history = []
        for a in assignments:
            item = _assignment_payload(a)
            history.append(item)
            cv = a.coverage
            if (
                cv
                and cv.event_date
                and cv.event_date >= today
                and a.status in ["assigned", "in_field"]
                and cv.status != "closed"
            ):
                upcoming.append(item)
        data = _journalist_to_card(j)
        data["skills"] = [s.strip() for s in (j.specialties or "").split(",") if s.strip()]
        data["upcoming"] = upcoming
        data["history"] = history
        data["updated_at"] = j.updated_at.isoformat() if j.updated_at else None
        return JsonResponse({"ok": True, "item": data})

    if request.method == "DELETE":
        j.delete()
        return JsonResponse({"ok": True})

    payload = _parse_body(request)
    changed = False
    for field in ("name", "email", "phone", "status", "specialties"):
        if field in payload:
            val = payload.get(field)
            if field in ("email", "phone") and isinstance(val, str) and not val.strip():
                val = None
            if isinstance(val, str):
                val = val.strip()
            setattr(j, field, val if val is not None else getattr(j, field))
            changed = True

    if "photo" in request.FILES:
        j.photo = request.FILES["photo"]
        changed = True

    if changed:
        j.save()

    return JsonResponse({"ok": True, "item": _journalist_to_card(j)})


@login_required
@require_http_methods(["GET", "POST"])
def api_drivers(request):
    if not _has_editorial_access(request.user):
        return _api_forbidden()

    if request.method == "GET":
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        sort = (request.GET.get("sort") or "").strip() or "name_asc"
        try:
            page = int(request.GET.get("page") or "1")
        except Exception:
            page = 1
        try:
            page_size = max(1, min(50, int(request.GET.get("page_size") or "24")))
        except Exception:
            page_size = 24

        qs = Driver.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        if status:
            qs = qs.filter(status=status)

        if sort == "name_desc":
            qs = qs.order_by("-name")
        elif sort == "created_desc":
            qs = qs.order_by("-created_at")
        elif sort == "status":
            qs = qs.order_by("status", "name")
        else:
            qs = qs.order_by("name")

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = [_driver_to_card(d) for d in qs[start:end]]
        num_pages = (total // page_size) + (1 if total % page_size else 0)
        return JsonResponse(
            {
                "ok": True,
                "items": items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "has_prev": page > 1,
                    "has_next": end < total,
                    "num_pages": num_pages,
                },
            }
        )

    payload = _parse_body(request)
    name = (payload.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "name_required"}, status=400)

    d = Driver.objects.create(
        name=name,
        phone=(payload.get("phone") or "").strip() or None,
        status=(payload.get("status") or "").strip() or "available",
    )
    if "photo" in request.FILES:
        d.photo = request.FILES["photo"]
        d.save(update_fields=["photo", "updated_at"])

    return JsonResponse({"ok": True, "item": _driver_to_card(d)}, status=201)


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def api_driver_detail(request, driver_id):
    if not _has_editorial_access(request.user):
        return _api_forbidden()

    d = Driver.objects.filter(id=driver_id).first()
    if not d:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    if request.method == "GET":
        assignments = (
            CoverageAssignment.objects.select_related("coverage")
            .filter(driver=d)
            .order_by("-assigned_at")
        )
        today = timezone.localdate()
        upcoming = []
        history = []
        for a in assignments:
            item = _assignment_payload(a)
            history.append(item)
            cv = a.coverage
            if (
                cv
                and cv.event_date
                and cv.event_date >= today
                and a.status in ["assigned", "in_field"]
                and cv.status != "closed"
            ):
                upcoming.append(item)
        data = _driver_to_card(d)
        data["upcoming"] = upcoming
        data["history"] = history
        data["updated_at"] = d.updated_at.isoformat() if d.updated_at else None
        return JsonResponse({"ok": True, "item": data})

    if request.method == "DELETE":
        d.delete()
        return JsonResponse({"ok": True})

    payload = _parse_body(request)
    changed = False
    for field in ("name", "phone", "status"):
        if field in payload:
            val = payload.get(field)
            if field == "phone" and isinstance(val, str) and not val.strip():
                val = None
            if isinstance(val, str):
                val = val.strip()
            setattr(d, field, val if val is not None else getattr(d, field))
            changed = True

    if "photo" in request.FILES:
        d.photo = request.FILES["photo"]
        changed = True

    if changed:
        d.save()

    return JsonResponse({"ok": True, "item": _driver_to_card(d)})
