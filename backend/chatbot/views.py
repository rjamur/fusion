import json
import requests
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .ai_service import gerar_resposta_ia

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def chatwoot_webhook(request):
    try:
        data = json.loads(request.body)
        
        # 1. SEGURANÇA BÁSICA: Validar se é uma mensagem criada
        event_type = data.get('event')
        if event_type != 'message_created':
            return JsonResponse({'status': 'ignored', 'reason': 'not_message_created'})

        # 2. EVITAR LOOP INFINITO: Só responder se for "incoming" (do cliente)
        message_type = data.get('message_type')
        if message_type != 'incoming':
            return JsonResponse({'status': 'ignored', 'reason': 'not_incoming_message'})

        # 3. EXTRAIR DADOS
        conversation_id = data.get('conversation', {}).get('id')
        user_message = data.get('content')
        
        if not user_message or not conversation_id:
            return JsonResponse({'status': 'error', 'reason': 'missing_data'})

        print(f"💬 Cliente disse: {user_message}")

        # 4. CHAMAR O CÉREBRO (IA)
        # (Aqui simplifiquei enviando só a última msg, depois podemos por histórico)
        historico = [{"role": "user", "content": user_message}]
        resposta_ia = gerar_resposta_ia(historico)

        print(f"🤖 IA respondeu: {resposta_ia}")

        # 5. RESPONDER AO CHATWOOT (Enviar a resposta de volta)
        enviar_para_chatwoot(conversation_id, resposta_ia)

        return JsonResponse({'status': 'success'})

    except Exception as e:
        print(f"🔥 Erro Crítico: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def enviar_para_chatwoot(conversation_id, text):
    """
    Empurra a mensagem da IA para dentro da conversa no Chatwoot via API
    """
    base_url = os.environ.get("CHATWOOT_BASE_URL")
    account_id = os.environ.get("CHATWOOT_ACCOUNT_ID")
    token = os.environ.get("CHATWOOT_API_TOKEN")

    url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    
    headers = {
        "api_access_token": token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "content": text,
        "message_type": "outgoing",
        "private": False 
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao enviar para Chatwoot: {response.text}")
