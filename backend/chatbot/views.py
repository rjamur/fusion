import json
import requests
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from . import services
from .models import Message
from .chatwoot_services import ChatwootAPI


# na sua views.py
import hmac
import hashlib
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt # Importante para webhooks de APIs externas

@csrf_exempt
def webhook_handler(request):
    # PASSO 1: Pegar os dados da requisição
    chatwoot_signature = request.headers.get('X-Chatwoot-Hmac-Sha256', '')
    request_body_bytes = request.body  # O corpo RAW em bytes
    secret_token = getattr(settings, 'CHATWOOT_BOT_TOKEN', '')

    # PASSO 2: Calcular sua própria assinatura
    digest_maker = hmac.new(
        secret_token.encode('utf-8'),
        msg=request_body_bytes,
        digestmod=hashlib.sha256
    )
    calculated_signature = digest_maker.hexdigest()

    # PASSO 3: IMPRIMIR TUDO PARA DEBUGAR!
    print("--- INICIANDO DEBUG DO WEBHOOK CHATWOOT ---")
    print(f"Segredo usado pelo Django: '{secret_token}'")
    print(f"Assinatura recebida do Chatwoot: '{chatwoot_signature}'")
    print(f"Assinatura calculada pelo Django: '{calculated_signature}'")

    # PASSO 4: Comparar as duas de forma segura
    if hmac.compare_digest(calculated_signature, chatwoot_signature):
        print(">>> SUCESSO: Assinatura válida! Requisição permitida.")
        # Coloque sua lógica de processamento do bot aqui
        # payload = json.loads(request_body_bytes)
        return HttpResponse("Webhook processado com sucesso.", status=200)
    else:
        print(">>> ERRO: Assinatura inválida! Requisição rejeitada.")
        return HttpResponseForbidden('Assinatura HMAC inválida.')


@csrf_exempt
def webhook_handler_bak(request):
    """
    Função que recebe as requisições de webhook do Chatwoot.
    """
    bot_token_header = request.headers.get('api_access_token')
    secret = getattr(settings, 'CHATWOOT_BOT_TOKEN', '!!! NÃO ENCONTRADO !!!')
    print(f"DEBUG: Segredo carregado no Django: '{secret}'")

    if not settings.CHATWOOT_BOT_TOKEN or bot_token_header != settings.CHATWOOT_BOT_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
        if payload.get('event') != 'message_created' or payload.get('message_type') != 'incoming':
            return JsonResponse({'status': 'ignored_event'}, status=200)

        conversation_id = payload.get('conversation', {}).get('id')
        message_content = payload.get('content')
        if not message_content or not conversation_id:
            return JsonResponse({'status': 'ignored_no_content_or_id'}, status=200)

        Message.objects.create(
            conversation_id=conversation_id,
            channel='chatwoot',
            sender='user',
            text=message_content
        )

        conversation_history = Message.objects.filter(
            channel='chatwoot',
            conversation_id=conversation_id
        ).order_by('created_at')

        bot_message_count = conversation_history.filter(sender='bot').count()

        # Limite de 3 perguntas (respostas do bot)
        if bot_message_count >= 3:
            # Lógica de transferência
            chatwoot_api = ChatwootAPI()
            chatwoot_api.toggle_conversation_status(conversation_id, status='open')
            # Desatribui o bot da conversa, colocando-a na fila geral
            chatwoot_api.assign_conversation(conversation_id, agent_id=0)

            final_message = "Obrigado por suas respostas. Estou transferindo você para um de nossos atendentes."
            Message.objects.create(
                conversation_id=conversation_id, channel='chatwoot', sender='bot', text=final_message
            )
            response_data = [{"content": final_message, "message_type": "outgoing"}]
            return JsonResponse(response_data, safe=False)
        else:
            # Lógica de IA para continuar a conversa
            system_prompt = settings.OPENAI_MEDICAL_PROMPT
            bot_response_content = services.get_ai_response(conversation_history, system_prompt=system_prompt)

            Message.objects.create(
                conversation_id=conversation_id,
                channel='chatwoot',
                sender='bot',
                text=bot_response_content
            )
            response_data = [{"content": bot_response_content, "message_type": "outgoing"}]
            return JsonResponse(response_data, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
