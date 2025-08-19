import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from . import services
from .models import Message
from .chatwoot_services import ChatwootAPI

logger = logging.getLogger(__name__)

# A view principal que RECEBE os webhooks
@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook_handler(request):
    """
    Recebe e processa webhooks do tipo 'Agent Bot' do Chatwoot.
    Implementa a lógica de IA e transferência para atendente humano.
    """
    # Validação de segurança por IP (conforme solicitado).
    # Este método é menos seguro que a validação por token.
    # O IP '172.25.0.4' foi identificado nos logs como o IP do container do Chatwoot.
    #CHATWOOT_CONTAINER_IP = '172.25.0.4'
    #requester_ip = request.META.get('REMOTE_ADDR')
    #if requester_ip != CHATWOOT_CONTAINER_IP:
    #    logger.warning(f"Requisição de IP não autorizado rejeitada: {requester_ip}")
    #    return HttpResponseForbidden('IP não autorizado.')

    try:
        payload = json.loads(request.body)

        # Filtros para ignorar eventos irrelevantes (ex: mensagens do próprio bot)
        if (payload.get('event') != 'message_created' or
            payload.get('message_type') != 'incoming' or
            payload.get('sender', {}).get('type') == 'agent_bot'):
            return JsonResponse({'status': 'ignored: not a new incoming user message'}, status=200)

        conversation_id = payload.get('conversation', {}).get('id')
        message_content = payload.get('content')

        if not message_content or not conversation_id:
            logger.warning("Webhook do Chatwoot ignorado: sem 'content' ou 'conversation_id'.")
            return JsonResponse({'status': 'ignored: no content or conversation_id'}, status=200)

        logger.info(f"Mensagem recebida do Chatwoot na conversa {conversation_id}: '{message_content}'")

        # 1. Salva a mensagem do usuário no nosso banco de dados
        Message.objects.create(
            conversation_id=str(conversation_id), channel='chatwoot', sender='user', text=message_content
        )

        # 2. Busca o histórico da conversa para dar contexto à IA
        conversation_history = Message.objects.filter(
            channel='chatwoot', conversation_id=str(conversation_id)
        ).order_by('created_at')

        # 3. Lógica de transferência: após 3 respostas do bot, transfere para um humano
        bot_message_count = conversation_history.filter(sender='bot').count()
        chatwoot_api = ChatwootAPI()
        if False: #bot_message_count >= 3:
            final_message = "Obrigado por suas respostas. Estou transferindo você para um de nossos atendentes."
            logger.info(f"Limite de mensagens atingido. Transferindo conversa {conversation_id} para um atendente.")
            Message.objects.create(
                conversation_id=str(conversation_id), channel='chatwoot', sender='bot', text=final_message
            )
            chatwoot_api.create_message(conversation_id, final_message)
            chatwoot_api.toggle_conversation_status(conversation_id, status='open')
            chatwoot_api.assign_conversation(conversation_id, agent_id=0)  # agent_id=0 desatribui o bot
            return JsonResponse({'status': 'ok, transferred to human'}, status=200)
        else:
            # 4. Se não for transferir, chama a IA para gerar uma resposta
            # O conteúdo do prompt define o comportamento do bot. A função get_ai_response agora usa Gemini.
            ai_medical_prompt = settings.AI_MEDICAL_PROMPT
            resposta_do_bot = services.get_ai_response(conversation_history, system_prompt=ai_medical_prompt)
            Message.objects.create(
                conversation_id=str(conversation_id), channel='chatwoot', sender='bot', text=resposta_do_bot
            )
            chatwoot_api.create_message(conversation_id, resposta_do_bot)
            return JsonResponse({'status': 'ok, bot replied'}, status=200)

    except json.JSONDecodeError:
        logger.error("Erro ao decodificar JSON do webhook do Chatwoot.", exc_info=True)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Erro inesperado ao processar webhook do Chatwoot: {e}", exc_info=True)
        # Retorna 200 para o Chatwoot não ficar tentando de novo
        return JsonResponse({'status': 'internal_error_acknowledged'}, status=200)
