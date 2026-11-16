import base64
import json
import mimetypes
import re
import uuid
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import ai
from .models import AICall, AIConfig, Record, Revision, Upload

APP_DIR = Path(__file__).resolve().parent / "static" / "app"
PATH_RE = re.compile(r"^(?!\.{1,2}(/|$))[A-Za-z0-9_\-.~:@+]{1,120}(/(?!\.{1,2}(/|$))[A-Za-z0-9_\-.~:@+]{1,120}){1,6}$")
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def api_login_required(view):
    """Like login_required, but answers 401 JSON instead of redirecting (the app shows the login page)."""
    @wraps(view)
    def wrapped(request, *a, **kw):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please sign in again.", "code": "auth"}, status=401)
        return view(request, *a, **kw)
    return wrapped


def body(request):
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        return None


# ---------- the app itself ----------
@login_required
@ensure_csrf_cookie
def index(request):
    f = APP_DIR / "index.html"
    if not f.exists():
        return HttpResponse("The app isn't built yet. Run: python tools/build_www.py --web", status=500)
    resp = HttpResponse(f.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    return resp


@login_required
def media(request, path):
    root = Path(settings.MEDIA_ROOT).resolve()
    f = (root / path).resolve()
    if root not in f.parents or not f.is_file():
        raise Http404
    resp = FileResponse(open(f, "rb"), content_type=mimetypes.guess_type(f.name)[0] or "application/octet-stream")
    resp["Cache-Control"] = "private, max-age=31536000, immutable"
    return resp


# ---------- data ----------
@require_GET
@api_login_required
def records(request):
    return JsonResponse({"rev": Revision.current(),
                         "records": {r.path: r.data for r in Record.objects.all()}})


@require_GET
@api_login_required
def rev(request):
    return JsonResponse({"rev": Revision.current()})


@require_POST
@api_login_required
def write(request):
    """{"writes": [[path, data], [path, null]]}: null deletes. All or nothing."""
    b = body(request)
    writes = (b or {}).get("writes")
    if not isinstance(writes, list) or not writes or len(writes) > 500:
        return JsonResponse({"error": "Nothing to save."}, status=400)
    for w in writes:
        if not (isinstance(w, list) and len(w) == 2 and isinstance(w[0], str) and PATH_RE.match(w[0])
                and (w[1] is None or isinstance(w[1], dict))):
            return JsonResponse({"error": f"Bad record: {str(w)[:80]}"}, status=400)
    with transaction.atomic():
        for path, data in writes:
            if data is None:
                Record.objects.filter(path=path).delete()
            else:
                Record(path=path, data=data).save()
        r = Revision.bump()
    return JsonResponse({"rev": r})


@require_POST
@api_login_required
def upload(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file."}, status=400)
    ctype = f.content_type or mimetypes.guess_type(f.name)[0] or ""
    if ctype not in IMAGE_TYPES:
        return JsonResponse({"error": "Only PNG, JPG, WebP or GIF images."}, status=400)
    if f.size > 8 * 1024 * 1024:
        return JsonResponse({"error": "Image is over 8 MB."}, status=400)
    ext = mimetypes.guess_extension(ctype) or ".bin"
    u = Upload(content_type=ctype)
    u.file.save(uuid.uuid4().hex + (".jpg" if ext == ".jpe" else ext), f, save=True)
    return JsonResponse({"url": u.url})


# ---------- AI ----------
def ai_state():
    cfg = AIConfig.get()
    k = cfg.key or ""
    return {
        "provider": cfg.provider, "base": cfg.base, "model": cfg.model,
        "hasKey": bool(k), "keyHint": ("…" + k[-4:]) if len(k) > 8 else ("set" if k else ""),
        "limit": cfg.monthly_token_limit, "ready": ai.is_ready(cfg), "usage": ai.month_usage(),
        "presets": ai.PRESETS,
    }


@require_http_methods(["GET", "POST"])
@api_login_required
def ai_config(request):
    if request.method == "POST":
        b = body(request) or {}
        cfg = AIConfig.get()
        if "provider" in b:
            if b["provider"] not in ai.PRESETS:
                return JsonResponse({"error": "Unknown provider."}, status=400)
            cfg.provider = b["provider"]
        for f in ("base", "model"):
            if f in b:
                setattr(cfg, f, str(b[f] or "").strip()[:300])
        if b.get("key"):
            cfg.key = str(b["key"]).strip()
        if b.get("clearKey"):
            cfg.key = ""
        if "limit" in b:
            try:
                cfg.monthly_token_limit = max(0, int(b["limit"] or 0))
            except (TypeError, ValueError):
                return JsonResponse({"error": "Limit must be a number."}, status=400)
        cfg.save()
    return JsonResponse(ai_state())


@require_POST
@api_login_required
def ai_complete(request):
    b = body(request) or {}
    try:
        r = ai.complete(b.get("prompt", ""), b.get("maxTokens") or 600, use_cache=b.get("cache", True) is not False)
    except ai.AIError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status)
    return JsonResponse(r)


@require_GET
@api_login_required
def ai_usage(request):
    last = [{"at": c.created.isoformat(), "model": c.model, "in": c.input_tokens, "out": c.output_tokens,
             "cached": c.cached, "ok": c.ok, "error": c.error} for c in AICall.objects.all()[:20]]
    return JsonResponse({"month": ai.month_usage(), "last": last})


# ---------- backup / restore ----------
def build_backup():
    blobs, records = {}, {}
    for u in Upload.objects.all():
        try:
            with u.file.open("rb") as fh:
                data = fh.read()
        except FileNotFoundError:
            continue
        blobs[u.url] = {"type": u.content_type, "b64": base64.b64encode(data).decode()}
    for r in Record.objects.all():
        records[r.path] = r.data
    return {"app": "radiant-billing", "version": 1, "exportedAt": timezone.now().isoformat(),
            "records": records, "blobs": blobs}


def _swap_refs(obj, mapping):
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    if isinstance(obj, list):
        return [_swap_refs(x, mapping) for x in obj]
    if isinstance(obj, dict):
        return {k: _swap_refs(v, mapping) for k, v in obj.items()}
    return obj


def import_backup(data, replace=True):
    """Loads a backup from this server, the Android app ("rl:<id>" photos) or the
    claude.ai artifact ("/_blob/<id>" photos). Photo references are rewritten to new uploads."""
    if not isinstance(data, dict) or not isinstance(data.get("records"), dict):
        raise ValueError("Not a Radiant Billing backup file.")
    mapping = {}
    with transaction.atomic():
        for ref, b in (data.get("blobs") or {}).items():
            raw = base64.b64decode(b["b64"])
            ctype = b.get("type") or "image/jpeg"
            ext = mimetypes.guess_extension(ctype) or ".jpg"
            u = Upload(content_type=ctype)
            u.file.save(uuid.uuid4().hex + (".jpg" if ext == ".jpe" else ext), ContentFile(raw), save=True)
            for alias in {ref, "rl:" + ref, "/_blob/" + ref, ref.split("/")[-1].split(".")[0]}:
                mapping[alias] = u.url
        if replace:
            Record.objects.all().delete()
        n = 0
        for path, rec in data["records"].items():
            if path.startswith(("blobs/", "meta/")) or not PATH_RE.match(path) or not isinstance(rec, dict):
                continue
            Record(path=path, data=_swap_refs(rec, mapping)).save()
            n += 1
        Revision.bump()
    return {"records": n, "photos": len(data.get("blobs") or {})}


@require_GET
@api_login_required
def backup(request):
    stamp = timezone.localtime().strftime("%Y-%m-%d-%H-%M")
    resp = HttpResponse(json.dumps(build_backup()), content_type="application/json")
    resp["Content-Disposition"] = f'attachment; filename="Radiant-Billing-backup-{stamp}.json"'
    return resp


@require_POST
@api_login_required
def restore(request):
    try:
        res = import_backup(body(request))
    except (ValueError, KeyError, TypeError) as e:
        return JsonResponse({"error": str(e) or "Couldn't read that backup."}, status=400)
    return JsonResponse(res)
