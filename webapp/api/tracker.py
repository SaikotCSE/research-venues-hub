"""Submission tracker endpoints: kanban board, submissions, checklists and papers."""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from tracker.forms import PaperForm, SubmissionForm
from tracker.models import ChecklistItem, Paper, Submission
from venues.models import Venue

from ..serializers import cycle_payload, iso, submission_payload
from .base import ApiError, endpoint, form_error, text

SUBMISSION_FIELDS = ("paper", "new_paper_title", "venue", "cycle", "status", "submitted_on", "decision_on", "notes")


def _board_qs(user):
    return user.submissions.select_related("paper", "venue", "cycle").annotate(
        items_total=Count("checklist_items", distinct=True),
        items_done=Count("checklist_items", filter=Q(checklist_items__done=True), distinct=True),
    )


@endpoint("GET", login=True)
def board(request):
    subs = list(_board_qs(request.user))
    by_status = {s: [] for s in Submission.BOARD_ORDER}
    for sub in subs:
        if sub.status in by_status:
            by_status[sub.status].append(submission_payload(sub))
    accepted = sum(1 for s in subs if s.status == "accepted")
    decided = sum(1 for s in subs if s.status in ("accepted", "rejected"))
    return {
        "columns": [{"key": k, "label": Submission.Status(k).label, "items": by_status[k]} for k in Submission.BOARD_ORDER],
        "statuses": [{"value": v, "label": label} for v, label in Submission.Status.choices],
        "stats": {
            "total": len(subs),
            "active": sum(1 for s in subs if s.status in Submission.ACTIVE),
            "accepted": accepted,
            "rate": round(100 * accepted / decided) if decided else None,
        },
    }


def _form_data(request, instance=None):
    """Translate the JSON body (venue by slug, ids for paper/cycle) into SubmissionForm data, keeping unspecified fields."""
    body = request.data
    data = {}
    if instance is not None:
        data = {
            "paper": instance.paper_id,
            "venue": instance.venue_id,
            "cycle": instance.cycle_id or "",
            "status": instance.status,
            "submitted_on": iso(instance.submitted_on) or "",
            "decision_on": iso(instance.decision_on) or "",
            "notes": instance.notes,
        }
    for key in SUBMISSION_FIELDS:
        if key in body:
            value = body[key]
            data[key] = "" if value is None else value
    if "venue" in body:
        venue = Venue.objects.filter(slug=body["venue"]).only("pk").first() if isinstance(body["venue"], str) else None
        data["venue"] = venue.pk if venue else ""
    return data


def submission_detail_payload(sub):
    venue = sub.venue
    return {
        **submission_payload(sub),
        "checklist_items": [{"id": i.id, "text": i.text, "done": i.done} for i in sub.checklist_items.all()],
        "venue_cycles": [cycle_payload(c) for c in venue.cycles.order_by("-year")],
        "venue_rank_label": venue.rank_label,
    }


@endpoint("GET", "POST", login=True)
def submissions(request):
    if request.method == "GET":
        return {"results": [submission_payload(s) for s in _board_qs(request.user)]}
    form = SubmissionForm(data=_form_data(request), user=request.user)
    if not form.is_valid():
        form_error(form)
    sub = form.save()
    sub.seed_checklist()
    return {"submission": submission_detail_payload(sub), "message": f"Tracking “{sub.paper}” for {sub.venue.acronym}."}


@endpoint("GET", "PATCH", "DELETE", login=True)
def submission(request, pk):
    sub = get_object_or_404(Submission.objects.select_related("paper", "venue", "cycle"), pk=pk, user=request.user)
    if request.method == "DELETE":
        sub.delete()
        return {"ok": True}
    if request.method == "PATCH":
        if set(request.data) == {"status"}:  # drag & drop on the board
            status = request.data["status"]
            if status not in Submission.Status.values:
                raise ApiError("Unknown status.", 400, {"status": ["Choose a valid status."]})
            if status != sub.status:
                sub.status = status
                sub.save()
        else:
            form = SubmissionForm(data=_form_data(request, sub), user=request.user, instance=sub)
            form.fields["paper"].required = True
            if not form.is_valid():
                form_error(form)
            sub = form.save()
        sub.refresh_from_db()
    sub.seed_checklist()
    return submission_detail_payload(sub)


@endpoint("POST", login=True)
def checklist_add(request, pk):
    sub = get_object_or_404(Submission, pk=pk, user=request.user)
    item_text = text(request.data, "text", 200)
    if not item_text:
        raise ApiError("Enter a checklist item.", 400, {"text": ["This field is required."]})
    item = ChecklistItem.objects.create(submission=sub, text=item_text, position=sub.checklist_items.count())
    return {"item": {"id": item.id, "text": item.text, "done": item.done}}


@endpoint("PATCH", "DELETE", login=True)
def checklist_item(request, pk, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id, submission__pk=pk, submission__user=request.user)
    if request.method == "DELETE":
        item.delete()
        return {"ok": True}
    if "done" in request.data:
        item.done = bool(request.data["done"])
    if "text" in request.data and text(request.data, "text", 200):
        item.text = text(request.data, "text", 200)
    item.save(update_fields=["done", "text"])
    return {"item": {"id": item.id, "text": item.text, "done": item.done}}


def _paper_payload(p):
    return {
        "id": p.id,
        "title": p.title,
        "abstract": p.abstract,
        "keywords": p.keywords,
        "created_at": iso(p.created_at),
        "submission_count": getattr(p, "n", None),
    }


@endpoint("GET", "POST", login=True)
def papers(request):
    if request.method == "POST":
        form = PaperForm(
            data={"title": text(request.data, "title", 250), "abstract": text(request.data, "abstract"), "keywords": text(request.data, "keywords", 300)}
        )
        if not form.is_valid():
            form_error(form)
        p = form.save(commit=False)
        p.user = request.user
        p.save()
        p.n = 0
        return {"paper": _paper_payload(p), "message": f"Added “{p.title}”."}
    return {"results": [_paper_payload(p) for p in request.user.papers.annotate(n=Count("submissions"))]}


@endpoint("PATCH", "DELETE", login=True)
def paper(request, pk):
    p = get_object_or_404(Paper, pk=pk, user=request.user)
    if request.method == "DELETE":
        p.delete()
        return {"ok": True}
    data = {f: text(request.data, f) if f in request.data else getattr(p, f) for f in ("title", "abstract", "keywords")}
    form = PaperForm(data=data, instance=p)
    if not form.is_valid():
        form_error(form)
    form.save()
    p.n = p.submissions.count()
    return {"paper": _paper_payload(p)}
