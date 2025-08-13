import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from chatbot.models import Message
from chatbot import services as chatbot_services

logger = logging.getLogger(__name__)

@csrf_exempt
def twilio_webhook_handler(request):
    if request.method == 'POST':
        try:
            # 1. Extrair dados do webhook do Twilio (vem como form data)
            conversation_id = request.POST.get('From')
            text = request.POST.get('Body')

            if not conversation_id or not text:
                logger.warning("Webhook do Twilio ignorado: 'From' ou 'Body' ausentes.")
                return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='text/xml')

            logger.info(f"Mensagem recebida de {conversation_id} via Twilio: '{text}'")

            # 2. Salva a mensagem do usuário no nosso banco de dados
            Message.objects.create(
                conversation_id=conversation_id,
                channel='twilio_whatsapp',
                sender='user',
                text=text
            )

            # 3. Busca o histórico completo da conversa no nosso BD
            conversation_history = Message.objects.filter(
                channel='twilio_whatsapp',
                conversation_id=conversation_id
            ).order_by('created_at')

            # 4. Gera a resposta usando o nosso serviço de "inteligência"
            bot_response_text = chatbot_services.get_ai_response(conversation_history)
            logger.info(f"Resposta da IA recebida: '{bot_response_text}'")

            if not bot_response_text or not bot_response_text.strip():
                logger.warning("A resposta da IA está vazia. Nenhuma mensagem será enviada.")
                return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='text/xml')

            # 5. Salva a resposta do bot no nosso banco de dados
            Message.objects.create(
                conversation_id=conversation_id,
                channel='twilio_whatsapp',
                sender='bot',
                text=bot_response_text
            )

            # 6. Envia a resposta da IA de volta para o usuário usando o dispatcher central
            chatbot_services.send_message_to_channel(
                channel='twilio_whatsapp',
                conversation_id=conversation_id,
                text=bot_response_text
            )
        except Exception as e:
            logger.error(f"Erro ao processar webhook do Twilio: {e}", exc_info=True)
            return HttpResponse(status=500)

        # Twilio espera uma resposta TwiML vazia para não enviar uma resposta automática de erro.
        return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='text/xml')

    return HttpResponse("Error: Method Not Allowed", status=405)
