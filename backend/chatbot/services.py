import logging

import google.generativeai as genai
from django.conf import settings

# Importa os serviços específicos de cada canal
from telegram_bridge import services as telegram_services
from twilio_bridge import services as twilio_services

logger = logging.getLogger(__name__)


def get_ai_response(conversation_history, system_prompt=None):
    """
    Gera uma resposta de IA usando a API do Google Gemini com base no histórico da conversa.
    Permite a especificação de um prompt de sistema customizado.
    """
    try:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.error("A variável de ambiente GEMINI_API_KEY não está configurada.")
            return "Desculpe, estou com um problema de configuração interna."

        genai.configure(api_key=api_key)

        # Usa o prompt de sistema padrão se nenhum for fornecido
        if system_prompt is None:
            system_prompt = settings.GEMINI_SYSTEM_PROMPT

        # Formata o histórico para a API do Gemini
        formatted_history = [
            {'role': 'user' if msg.sender == 'user' else 'model', 'parts': [msg.text]}
            for msg in conversation_history
        ]

        logger.info(f"Enviando para a API do Gemini. Histórico: {formatted_history}")

        model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            system_instruction=system_prompt
        )
        chat = model.start_chat(history=formatted_history[:-1])
        response = chat.send_message(formatted_history[-1]['parts'][0])

        logger.info(f"Resposta recebida da API do Gemini: '{response.text}'")

        return response.text
    except Exception as e:
        logger.error(f"Erro ao chamar a API do Gemini: {e}")
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