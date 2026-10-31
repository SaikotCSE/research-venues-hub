from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from venues.models import DeadlineCycle, Venue

from .forms import PaperForm, SubmissionForm
from .models import ChecklistItem, Paper, Submission


@login_required
def board(request):
    subs = request.user.submissions.select_related("paper", "venue", "cycle")
    by_status = {s: [] for s in Submission.BOARD_ORDER}
    for sub in subs:
        if sub.status in by_status:
            by_status[sub.status].append(sub)
    columns = [{"key": k, "label": Submission.Status(k).label, "items": by_status[k]} for k in Submission.BOARD_ORDER]
    decided = request.user.submissions.filter(status__in=["accepted", "rejected"])
    acc = decided.filter(status="accepted").count()
    stats = {"total": subs.count(), "active": subs.filter(status__in=Submission.ACTIVE).count(), "accepted": acc,
             "rate": round(100 * acc / decided.count()) if decided.count() else None}
    return render(request, "tracker/board.html", {"columns": columns, "stats": stats, "statuses": Submission.Status.choices})


@login_required
def submission_create(request):
    initial = {}
    slug = request.GET.get("venue")
    if slug:
        venue = Venue.objects.filter(slug=slug).first()
        if venue:
            initial["venue"] = venue
            cycle = venue.next_cycle
            if cycle:
                initial["cycle"] = cycle
    form = SubmissionForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        sub = form.save()
        sub.seed_checklist()
        messages.success(request, f"Tracking “{sub.paper}” for {sub.venue.acronym}.")
        return redirect("tracker:detail", pk=sub.pk)
    return render(request, "accounts/form_page.html", {"form": form, "title": "Track a submission", "submit": "Start tracking"})


@login_required
def submission_detail(request, pk):
    sub = get_object_or_404(Submission.objects.select_related("paper", "venue", "cycle"), pk=pk, user=request.user)
    form = SubmissionForm(request.POST or None, user=request.user, instance=sub, initial={"new_paper_title": ""})
    if request.method == "POST":
        form.fields["paper"].required = True
        if form.is_valid():
            form.save()
            messages.success(request, "Saved.")
            return redirect("tracker:detail", pk=pk)
    sub.seed_checklist()
    return render(request, "tracker/detail.html", {"sub": sub, "form": form, "items": sub.checklist_items.all()})


@login_required
@require_POST
def submission_status(request, pk):
    sub = get_object_or_404(Submission, pk=pk, user=request.user)
    status = request.POST.get("status")
    if status in Submission.Status.values:
        sub.status = status
        sub.save()
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    return redirect("tracker:board")


@login_required
@require_POST
def submission_delete(request, pk):
    get_object_or_404(Submission, pk=pk, user=request.user).delete()
    return redirect("tracker:board")


@login_required
@require_POST
def checklist_toggle(request, pk, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id, submission__pk=pk, submission__user=request.user)
    item.done = not item.done
    item.save(update_fields=["done"])
    return render(request, "tracker/partials/checklist_item.html", {"item": item})


@login_required
@require_POST
def checklist_add(request, pk):
    sub = get_object_or_404(Submission, pk=pk, user=request.user)
    text = request.POST.get("text", "").strip()[:200]
    if text:
        ChecklistItem.objects.create(submission=sub, text=text, position=sub.checklist_items.count())
    return redirect("tracker:detail", pk=pk)


@login_required
def papers(request):
    form = PaperForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        p = form.save(commit=False)
        p.user = request.user
        p.save()
        return redirect("tracker:papers")
    items = request.user.papers.annotate(n=Count("submissions"))
    return render(request, "tracker/papers.html", {"papers": items, "form": form})


@login_required
@require_POST
def paper_delete(request, pk):
    get_object_or_404(Paper, pk=pk, user=request.user).delete()
    return redirect("tracker:papers")
