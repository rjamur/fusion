import logging
import openai
from django.conf import settings

# Importa os serviços específicos de cada canal
from telegram_bridge import services as telegram_services
from twilio_bridge import services as twilio_services

logger = logging.getLogger(__name__)


def get_ai_response(conversation_history, system_prompt=None):
    """
    Gera uma resposta de IA usando a API da OpenAI com base no histórico da conversa.
    Permite a especificação de um prompt de sistema customizado.
    """
    try:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.error("A variável de ambiente OPENAI_API_KEY não está configurada.")
            return "Desculpe, estou com um problema de configuração interna."

        openai.api_key = api_key

        if system_prompt is None:
            system_prompt = "Você é um assistente virtual."

        # Formata o histórico para a API da OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            role = "user" if msg.sender == 'user' else "assistant"
            messages.append({"role": role, "content": msg.text})

        logger.info(f"Enviando para a API da OpenAI. Mensagens: {messages}")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )

        bot_response = response.choices[0].message['content'].strip()
        logger.info(f"Resposta recebida da API da OpenAI: '{bot_response}'")

        return bot_response
    except Exception as e:
        logger.error(f"Erro ao chamar a API da OpenAI: {e}")
        return "Desculpe, estou com problemas para me conectar com minha inteligência. Tente novamente mais tarde."


def send_message_to_channel(channel, conversation_id, text):
    """
    Dispatcher que envia uma mensagem para o canal correto.
    Esta função centraliza a lógica de envio, tornando as views mais limpas.
    """
    logger.info(f"Disparando mensagem para o canal '{channel}' para a conversa '{conversation_id}'")
    if channel == 'telegram':
        telegram_services.send_telegram_message(chat_id=conversation_id, text=text)
    elif channel == 'twilio_whatsapp':
        twilio_services.send_twilio_whatsapp_message(recipient_id=conversation_id, text=text)
    else:
        logger.error(f"Tentativa de enviar mensagem para um canal desconhecido: {channel}")