import json
import requests
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from . import services
from .models import Message

@csrf_exempt
def webhook_handler(request):
    """
    Função que recebe as requisições de webhook do Chatwoot.
    """
    # --- Verificação de Segurança ---
    # Verifica se o token enviado pelo Chatwoot no header 'api_access_token'
    # corresponde ao token de segurança do nosso bot.
    # Isso garante que a requisição é legítima.
    bot_token_header = request.headers.get('api_access_token')
    if not settings.CHATWOOT_BOT_TOKEN or bot_token_header != settings.CHATWOOT_BOT_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)

            # --- Lógica de Controle ---
            # 1. Processar apenas eventos de criação de mensagem de usuários.
            # Isso previne o bot de responder a si mesmo (loop infinito).
            if payload.get('event') != 'message_created' or payload.get('message_type') != 'incoming':
                return JsonResponse({'status': 'ignored_event'}, status=200)

            conversation_id = payload.get('conversation', {}).get('id')
            message_content = payload.get('content')
            if not message_content or not conversation_id:
                return JsonResponse({'status': 'ignored_no_content_or_id'}, status=200)

            # Salva a mensagem do usuário no nosso banco de dados
            Message.objects.create(
                conversation_id=conversation_id,
                channel='chatwoot',
                sender='user',
                text=message_content
            )

            # --- Lógica de Resposta Refatorada ---
            # 1. Busca o histórico completo da conversa no nosso BD
            conversation_history = Message.objects.filter(
                channel='chatwoot',
                conversation_id=conversation_id
            ).order_by('created_at')

            # 2. Gera a resposta usando o nosso serviço de "inteligência" com o histórico
            bot_response_content = services.get_ai_response(conversation_history)

            # 2. Salva a resposta do bot no nosso banco de dados
            Message.objects.create(
                conversation_id=conversation_id,
                channel='chatwoot',
                sender='bot',
                text=bot_response_content
            )

            # 3. Retorna a resposta no formato esperado pelo Agent Bot
            # O Chatwoot espera uma lista de objetos de mensagem.
            response_data = [
                {
                    "content": bot_response_content,
                    "message_type": "outgoing"
                }
            ]
            print(f"Enviando resposta para o Agent Bot: {response_data}")
            return JsonResponse(response_data, safe=False)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    return HttpResponse(status=405) # Method Not Allowed
