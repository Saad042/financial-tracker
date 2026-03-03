from django.urls import path

from . import views

app_name = "tags"

urlpatterns = [
    path("", views.TagListView.as_view(), name="list"),
    path("add/", views.TagCreateView.as_view(), name="create"),
    path("groups/", views.TagGroupsView.as_view(), name="groups"),
    path("places/", views.TagPlacesView.as_view(), name="places"),
    path("search/", views.tag_search, name="search"),
    path("create-inline/", views.tag_create_inline, name="create_inline"),
    path("<int:pk>/", views.TagDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.TagUpdateView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.TagArchiveView.as_view(), name="archive"),
]
