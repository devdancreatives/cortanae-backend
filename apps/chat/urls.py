from django.urls import path
from . import views

urlpatterns = [
    path("", views.RoomListAPIView.as_view(), name="api-room-list"),
    path(
        "create_room/",
        views.GetORCreateChatRoomView.as_view(),
        name="api-reciever-id",
    ),
    path(
        "room/<uuid:room_id>/<uuid:receiver_id>/",
        views.RoomAPIView.as_view(),
        name="room-details",
    ),
    path(
        "update_has_seen/<uuid:room_id>/<uuid:receiver_id>/",
        views.UpdateHasSeenAPIView.as_view(),
        name="update_has_seen",
    ),
]
