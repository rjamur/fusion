import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chatbot.models import Message
from chatbot import services as chatbot_services

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook_handler(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            logger.info(f"Webhook do Telegram recebido.")

            # Extrai as informações essenciais do payload do Telegram.
            # Usamos .get() para evitar erros caso a estrutura do JSON seja inesperada.
            message = payload.get('message')
            if not message:
                logger.warning("Webhook ignorado: payload não contém a chave 'message'.")
                return JsonResponse({"status": "ok_no_message"})

            chat_id = message.get('chat', {}).get('id')
            if not chat_id:
                logger.warning("Webhook ignorado: não foi possível extrair o chat_id.")
                return JsonResponse({"status": "ok_no_chat_id"})

            text = message.get('text')
            if not text:
                logger.info("Webhook ignorado: mensagem sem conteúdo de texto.")
                return JsonResponse({"status": "ok_no_text"})
            logger.info(f"Mensagem recebida do chat_id {chat_id}: '{text}'")

            # 1. Salva a mensagem do usuário no nosso banco de dados
            Message.objects.create(
                conversation_id=chat_id,
                channel='telegram',
                sender='user',
                text=text
            )

            # 2. Busca o histórico completo da conversa no nosso BD
            # O .order_by('created_at') garante a ordem cronológica.
            conversation_history = Message.objects.filter(
                channel='telegram',
                conversation_id=chat_id
            ).order_by('created_at')

            # 3. Gera a resposta usando o nosso serviço de "inteligência"
            bot_response_text = chatbot_services.get_ai_response(conversation_history)
            logger.info(f"Resposta da IA recebida: '{bot_response_text}'")

            # Adiciona uma verificação para não enviar mensagens vazias
            if not bot_response_text or not bot_response_text.strip():
                logger.warning("A resposta da IA está vazia. Nenhuma mensagem será enviada.")
                return JsonResponse({"status": "ok_empty_ai_response"})

            # 4. Salva a resposta do bot no nosso banco de dados
            Message.objects.create(
                conversation_id=chat_id,
                channel='telegram',
                sender='bot',
                text=bot_response_text
            )

            # 5. Envia a resposta da IA de volta para o usuário usando o dispatcher central
            chatbot_services.send_message_to_channel(
                channel='telegram',
                conversation_id=chat_id,
                text=bot_response_text
            )

            return JsonResponse({"status": "ok"})
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON do Telegram.")
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Method Not Allowed"}, status=405)
