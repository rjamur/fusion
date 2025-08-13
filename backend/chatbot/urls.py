from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # This is the endpoint that the Chatwoot Agent Bot will call.
    path('webhook/chatwoot/', views.webhook_handler, name='chatwoot_webhook'),
]