from django.urls import reverse


def nav(request):
    user = getattr(request, "user", None)
    authed = user is not None and user.is_authenticated
    nav_links = [
        (reverse("venues:list"), "Explore"),
        (reverse("venues:recommend"), "Recommend"),
        (reverse("venues:plan"), "Planner"),
        (reverse("venues:insights"), "Insights"),
        (reverse("venues:targets"), "My Targets"),
    ]
    if authed:
        nav_links.append((reverse("tracker:board"), "Tracker"))
    user_links = [
        (reverse("accounts:dashboard"), "Dashboard"),
        (reverse("tracker:board"), "Submission tracker"),
        (reverse("tracker:papers"), "My papers"),
        (reverse("accounts:lists"), "My lists"),
        (reverse("accounts:profile"), "Profile & API token"),
    ]
    return {
        "unread_count": user.notifications.filter(read_at__isnull=True).count() if authed else 0,
        "nav_links": nav_links, "user_links": user_links,
    }
